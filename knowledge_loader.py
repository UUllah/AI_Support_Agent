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
    Joins TicketDetails (1:1) and Ticket_Comments (1:many) per ticket.
    Groups comments by IssueID and aggregates with ticket details.
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

    # Query joining TicketDetails and Ticket_Comments
    query = """
    SELECT
        td.IssueID as ticket_id,
        td.Subject as subject,
        td.Summary as summary,
        tc.Body as comment_body,
        tc.CommentDate as comment_date
    FROM TicketDetails td
    LEFT JOIN Ticket_Comments tc ON td.IssueID = tc.IssueID
    WHERE tc.IsSystem = 0
      AND tc.Body IS NOT NULL
      AND YEAR(tc.CommentDate) = 2026
    ORDER BY td.IssueID, tc.CommentDate
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    # Group comments by ticket_id
    tickets = defaultdict(lambda: {
        'ticket_id': None,
        'subject': '',
        'summary': '',
        'comments': []
    })

    for row in rows:
        ticket_id = row.ticket_id
        if tickets[ticket_id]['ticket_id'] is None:
            tickets[ticket_id]['ticket_id'] = ticket_id
            tickets[ticket_id]['subject'] = row.subject or ''
            tickets[ticket_id]['summary'] = row.summary or ''

        # Clean and add comment
        clean_comment_text = clean_comment(row.comment_body)
        if clean_comment_text:
            tickets[ticket_id]['comments'].append({
                'text': clean_comment_text,
                'date': row.comment_date
            })

    # Create structured ticket objects
    structured_tickets = []
    for ticket_id, ticket_data in tickets.items():
        # Combine subject, summary, and comments for full_text
        comments_text = '\n'.join([c['text'] for c in ticket_data['comments']])
        full_text = f"{ticket_data['subject']} {ticket_data['summary']} {comments_text}".strip()

        structured_ticket = {
            'ticket_id': ticket_data['ticket_id'],
            'subject': ticket_data['subject'],
            'summary': ticket_data['summary'],
            'comments': ticket_data['comments'],
            'full_text': full_text
        }
        structured_tickets.append(structured_ticket)

    conn.close()
    return structured_tickets

# Example usage
if __name__ == "__main__":
    conversations = load_ticket_conversations()
    print(f"Loaded {len(conversations)} conversations.")
    print(conversations[0])  # Print first conversation for verification