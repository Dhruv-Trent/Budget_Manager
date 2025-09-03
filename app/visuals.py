import matplotlib.pyplot as plt
from io import BytesIO
import base64

def plot_category_expenses(expenses_by_category):
    fig, ax = plt.subplots()
    categories = list(expenses_by_category.keys())
    amounts = list(expenses_by_category.values())
    ax.pie(amounts, labels=categories, autopct='%1.1f%%')
    ax.set_title("Spending by Category")

    # Save to base64 for HTML
    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return img_base64
