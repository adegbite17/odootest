from odoo import models, fields, api
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

LARGE_AMOUNT_THRESHOLD = 10_000_000
RAPID_TX_LIMIT = 5
RAPID_TX_WINDOW = 10


class BankTransaction(models.Model):
    _name = 'bank.transaction'
    _description = 'Bank Transaction'
    _order = 'transaction_date desc'

    name = fields.Char('Reference', required=True, copy=False, default='New')
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, index=True)
    amount = fields.Monetary('Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.NGN'), required=True)
    transaction_date = fields.Datetime('Transaction Date', required=True, default=fields.Datetime.now, index=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('flagged', 'Flagged'),
    ], default='pending', index=True, copy=False)
    flag_reason = fields.Text('Flag Reason', readonly=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Transaction reference must be unique.'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('bank.transaction') or 'New'
        return super().create(vals)

    @api.model
    def process_transactions(self):
        """Cron entry point: process all pending transactions."""
        pending = self.search([('state', '=', 'pending')], order='transaction_date asc')
        if not pending:
            return

        _logger.info("Processing %d pending transaction(s).", len(pending))

        # Pre compute rapid-transaction offenders in one query
        rapid_customers = self._get_rapid_transaction_customers(pending.mapped('customer_id').ids)

        for tx in pending:
            try:
                self._process_single(tx, rapid_customers)
            except Exception:
                _logger.exception("Error processing transaction %s", tx.name)

    def _process_single(self, tx, rapid_customers):
        reasons = []

        if tx.amount >= LARGE_AMOUNT_THRESHOLD:
            reasons.append(f"Amount ₦{tx.amount:,.2f} meets or exceeds ₦10,000,000 threshold.")

        if tx.customer_id.id in rapid_customers:
            reasons.append(
                f"Customer made more than {RAPID_TX_LIMIT} transactions within {RAPID_TX_WINDOW} minutes."
            )

        if reasons:
            tx.write({'state': 'flagged', 'flag_reason': '\n'.join(reasons)})
            _logger.warning("Flagged transaction %s: %s", tx.name, '; '.join(reasons))
        else:
            tx.write({'state': 'processed'})

    @api.model
    def _get_rapid_transaction_customers(self, customer_ids):
        """Return set of customer IDs with >5 transactions in any rolling 10-min window."""
        if not customer_ids:
            return set()

        window_start = fields.Datetime.now() - timedelta(minutes=RAPID_TX_WINDOW)


        self.env.cr.execute("""
            SELECT customer_id
            FROM bank_transaction
            WHERE customer_id = ANY(%s)
              AND transaction_date >= %s
            GROUP BY customer_id
            HAVING COUNT(*) > %s
        """, (customer_ids, window_start, RAPID_TX_LIMIT))

        return {row[0] for row in self.env.cr.fetchall()}
