import pyodbc
from collections import defaultdict
import re

def clean_comment(text):
    """
    Remove HTML tags and comments from the ticket body.
    """
    text = re.sub(r'<!--.*?-->', '', text)  # remove HTML comments
    text = re.sub(r'<.*?>', '', text)       # remove HTML tags
    return text.strip()

def load_ticket_conversations():
    """
    Load and clean ticket conversations from Jitbit Helpdesk database.
    Only includes human comments (IsSystem = 0).
    Groups comments by IssueID.
    """

    # Connect to SQL Server
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=172.16.0.22;"
        "DATABASE=jitbitHelpDesk;"
        "UID=ubaid;"
        "PWD=Avanza@123;"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
    )

    cursor = conn.cursor()

    # Query only non-system comments
    query = """
    SELECT 
        CommentID,
        IssueID,
        CommentDate,
        UserID,
        Body
    FROM hdComments
    WHERE IsSystem = 0
      AND Body IS NOT NULL AND year(CommentDate) = '2026' 
    ORDER BY IssueID, CommentDate
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    # Group comments by IssueID
    tickets = defaultdict(list)
    for row in rows:
        # Use row.IssueID, not row.TicketID
        tickets[row.IssueID].append(clean_comment(row.Body))

    # Combine each ticket's comments into one conversation
    conversations = []
    for ticket_id, msgs in tickets.items():
        text = "\n".join(msgs)
        conversations.append(text)

    return conversations

# Example usage
if __name__ == "__main__":
    conversations = load_ticket_conversations()
    print(f"Loaded {len(conversations)} conversations.")
    print(conversations[0])  # Print first conversation for verification