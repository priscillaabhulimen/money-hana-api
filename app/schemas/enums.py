from enum import Enum

class IncomeCategory(str, Enum):
    salary_wages = "salary_wages"
    returns = "returns"
    gift = "gift"
    other = "other"

class ExpenseCategory(str, Enum):
    groceries = "groceries"
    dining = "dining"
    transport = "transport"
    entertainment = "entertainment"
    utilities_bills = "utilities_bills"
    education = "education"
    subscriptions = "subscriptions"
    other = "other"