import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import argparse
from datetime import datetime

def load_json_file(file_path):
    """Load a JSON file and return its contents."""
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

def filter_posts_by_date(posts, start_date, end_date):
    """Filter posts to include only those within the specified date range."""
    filtered_posts = []
    for post in posts:
        post_date_str = post.get('date')  # Assuming posts have a 'date' field
        if post_date_str:
            post_date = datetime.fromisoformat(post_date_str)
            if start_date <= post_date <= end_date:
                filtered_posts.append(post)
    return filtered_posts

def combine_posts_and_edits(posts, edits):
    """Combine posts with their respective edits based on post IDs."""
    for edit in edits:
        post_id = edit.get('post_id')
        edit_content = edit.get('content')

        # Find the post to which this edit belongs
        for post in posts:
            if post.get('id') == post_id:
                # Assuming 'edits' field exists, or create one
                if 'edits' not in post:
                    post['edits'] = []
                post['edits'].append(edit_content)
                break

    return posts

def generate_pdf_from_posts(posts, output_pdf_path):
    """Generate a PDF document from combined post content."""
    buffer = canvas.Canvas(output_pdf_path, pagesize=letter)
    width, height = letter
    text_obj = buffer.beginText(40, height - 40)

    for post in posts:
        text_obj.setFont("Helvetica", 12)
        post_content = post.get('content', "No Content")
        text_obj.textLines(f"Post ID: {post.get('id', 'Unknown ID')}")
        text_obj.textLines(f"Date: {post.get('date', 'Unknown Date')}")
        text_obj.textLines(f"Original Post:\n{post_content}")

        # Add edits if any
        if 'edits' in post:
            for idx, edit in enumerate(post['edits'], start=1):
                text_obj.textLines(f"Edit {idx}:\n{edit}")

        text_obj.textLines("\n" + "-" * 60 + "\n")

    buffer.drawText(text_obj)
    buffer.save()
    print(f"PDF saved as {output_pdf_path}")

def main(posts_file_path, edits_file_path, output_pdf_path, start_date, end_date):
    # Load the JSON files
    posts = load_json_file(posts_file_path)
    edits = load_json_file(edits_file_path)

    # Filter posts by date range
    filtered_posts = filter_posts_by_date(posts, start_date, end_date)

    # Combine posts with edits
    combined_data = combine_posts_and_edits(filtered_posts, edits)

    # Generate PDF from the combined data
    generate_pdf_from_posts(combined_data, output_pdf_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Combine Facebook post data and convert to PDF.')
    parser.add_argument('--posts', required=True, help='Path to the JSON file containing Facebook posts.')
    parser.add_argument('--edits', required=True, help='Path to the JSON file containing post edits.')
    parser.add_argument('--output', default='combined_posts.pdf', help='Output PDF file path.')
    parser.add_argument('--start-date', required=True, help='Start date for filtering posts (YYYY-MM-DD).')
    parser.add_argument('--end-date', required=True, help='End date for filtering posts (YYYY-MM-DD).')

    args = parser.parse_args()

    # Parse the start and end dates
    start_date = datetime.fromisoformat(args.start_date)
    end_date = datetime.fromisoformat(args.end_date)

    main(args.posts, args.edits, args.output, start_date, end_date)

