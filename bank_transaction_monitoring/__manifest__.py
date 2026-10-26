{
    'name': 'Bank Transaction Monitoring',
    'version': '1.0',
    'summary': 'Automated monitoring of bank transactions for compliance',
    'category': 'Accounting',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/scheduled_action.xml',
        'views/bank_transaction_view.xml',
    ],
    'installable': True,
    'application': True,
}
