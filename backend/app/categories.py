"""Transaction category labels from Pluggy's published category tree.

Source: https://v1.docs.pluggy.ai/docs/transaction-categories
"""

CATEGORY_GROUPS: dict[str, tuple[str, ...]] = {
    "Income": ("Income", "Salary/pro-labore", "Salary", "Retirement", "Entrepreneurial activities", "Government aid", "Non-recurring income"),
    "Loans and Financing": ("Loans and Financing", "Late payment and overdraft costs", "Interests charged", "Loans", "Financing", "Real estate financing", "Vehicle Financing", "Student loan"),
    "Investments": ("Investments", "Automatic investment", "Fixed income", "Fixed Income Investment", "Mutual funds", "Variable income", "Margin", "Proceeds interests and dividends", "Pension"),
    "Same person transfer": ("Same person transfer", "Same person transfer - Cash", "Same person transfer - PIX", "Same person transfer - TED"),
    "Transfers": ("Transfers", "Transfer", "Transfer - Bank slip (Boleto)", "Transfer - Cash", "Transfer - Check", "Transfer - DOC", "Transfer - Foreign exchange", "Transfer - Internal", "Transfer - PIX", "Transfer - TED", "Credit card payment", "Third-party transfers", "Bank slip", "Debt card", "DOC", "PIX", "TED"),
    "Legal obligations": ("Legal obligations", "Blocked balances", "Alimony"),
    "Services": ("Services", "Telecommunications", "Internet", "Mobile", "TV", "Education", "Online Courses", "University", "School", "Kindergarten", "Wellness and fitness", "Gyms and fitness centers", "Sports practice", "Wellness", "Tickets", "Stadiums and arenas", "Landmarks and museums", "Cinema, theater and concerts"),
    "Shopping": ("Shopping", "Online shopping", "Electronics", "Pet supplies and vet", "Clothing", "Kids and toys", "Bookstore", "Sports goods", "Office Supplies"),
    "Cashback": ("Cashback",),
    "Digital services": ("Digital services", "Gaming", "Video streaming", "Music streaming"),
    "Groceries": ("Groceries",),
    "Food and drinks": ("Food and drinks", "Eating out", "Food delivery"),
    "Travel": ("Travel", "Airport and airlines", "Accommodation", "Mileage programs", "Bus tickets"),
    "Donations": ("Donations",),
    "Gambling": ("Gambling", "Lottery", "Online bet"),
    "Taxes": ("Taxes", "Income taxes", "Taxes on investments", "Tax on financial operations"),
    "Bank fees": ("Bank fees", "Account fees", "Wire transfer fees and ATM fees", "Credit card fees"),
    "Housing": ("Housing", "Rent", "Houseware", "Urban land and building tax", "Utilities", "Water", "Electricity", "Gas"),
    "Healthcare": ("Healthcare", "Dentist", "Pharmacy", "Optometry", "Hospital clinics and labs"),
    "Transportation": ("Transportation", "Taxi and ride-hailing", "Public transportation", "Car rental", "Bicycle", "Automotive", "Gas stations", "Parking", "Tolls and in-vehicle payment", "Vehicle ownership taxes and fees", "Vehicle maintenance", "Traffic tickets"),
    "Insurance": ("Insurance", "Life insurance", "Home Insurance", "Health insurance", "Vehicle insurance"),
    "Leisure": ("Leisure",),
    "Other": ("Other",),
    "Uncategorized": ("Uncategorized",),
}

CATEGORIES = list(dict.fromkeys(category for group in CATEGORY_GROUPS.values() for category in group))

LEGACY_CATEGORIES = {
    "Alimentação": "Food and drinks",
    "Transporte": "Transportation",
    "Moradia": "Housing",
    "Saúde": "Healthcare",
    "Educação": "Education",
    "Lazer": "Leisure",
    "Compras": "Shopping",
    "Contas e serviços": "Services",
    "Transferência": "Transfers",
    "Receita": "Income",
    "Investimentos": "Investments",
    "Outros": "Other",
    "Não categorizado": "Uncategorized",
}
