import json
import os.path

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import argparse
from datetime import datetime


def parseargs():
    parser = argparse.ArgumentParser(
        description="Combine Facebook post data and convert to PDF."
    )
    parser.add_argument(
        "--posts",
        required=True,
        help="Path to the JSON file containing Facebook posts.",
    )
    parser.add_argument(
        "--edits", required=True, help="Path to the JSON file containing post edits."
    )
    parser.add_argument(
        "--output", default="combined_posts.pdf", help="Output PDF file path."
    )
    parser.add_argument(
        "--start-date",
        default="2005-01-01",
        help="Start date for filtering posts (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end-date",
        default=str(datetime.now().date()),
        help="End date for filtering posts (YYYY-MM-DD).",
    )

    return parser.parse_args()


def load_json_file(file_path):
    """Load a JSON file and return its contents."""
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def get_post_timestamp_or_backdated(post):
    post_timestamp = post.get("timestamp")
    post_backdated_list = [
        d.get("backdated_timestamp")
        for d in post.get("data", [])
        if "backdated_timestamp" in d.keys()
    ]
    if len(post_backdated_list) != 0:
        post_timestamp = post_backdated_list[0]
    return post_timestamp


def filter_posts_by_date(posts, start_date, end_date):
    """Filter posts to include only those within the specified date range."""
    filtered_posts = []
    for post in posts:
        post_timestamp = get_post_timestamp_or_backdated(post)
        if post_timestamp:
            post_date = datetime.fromtimestamp(post_timestamp)
            if start_date <= post_date <= end_date:
                filtered_posts.append(post)
    return filtered_posts


def get_first_or_none(data_list):
    return data_list[0] if data_list else None


def flatten_post_data(posts):
    for post in posts:
        post_content = None
        for d in post.get("data", []):
            if "post" in d:
                content = d["post"]
                if post_content is None:
                    post_content = content
                else:
                    "\n".join([post_content, content])
        post["content"] = post_content
    return posts

def combine_posts_and_edits(posts, edits):
    """Combine posts with their respective edits based on post IDs."""
    for edit in edits:
        post_id = edit.get("timestamp")
        # .[].label_values[].value
        edit_content = get_first_or_none([lv.get("value") for lv in edit.get("label_values") if lv.get("ent_field_name") == "Text"])

        # Find the post to which this edit belongs
        for post in posts:
            if post.get("timestamp") == post_id:
                # Assuming 'edits' field exists, or create one
                if "edits" not in post:
                    post["edits"] = []
                post["edits"].append(edit_content)
                break

    return posts


def generate_pdf_from_posts(posts, output_pdf_path):
    """Generate a PDF document from combined post content."""
    buffer = canvas.Canvas(output_pdf_path, pagesize=letter)
    width, height = letter
    text_obj = buffer.beginText(40, height - 40)

    count = 0
    for post in posts:
        count += 1
        text_obj.setFont("Helvetica", 12)
        post_content = post.get("content")
        text_obj.textLines(f"Post ID: {post.get('title', 'Unknown ID')}")
        dt = datetime.fromtimestamp(get_post_timestamp_or_backdated(post))
        post["date"] = dt.strftime("%Y-%m-%dT%H:%M:%S")
        text_obj.textLines(f"Date: {dt.date()}")
        print(f"Getting {count}/{len(posts)} : {dt.date()}")
        text_obj.textLines(f"Original Post:\n{post_content}")

        # Add edits if any
        if "edits" in post:
            for idx, edit in enumerate(post["edits"], start=1):
                text_obj.textLines(f"Edit {idx}:\n{edit}")

        text_obj.textLines("\n" + "-" * 60 + "\n")

    buffer.drawText(text_obj)
    buffer.save()
    print(f"PDF saved as {output_pdf_path}")
    output_json_path = output_pdf_path.replace('.pdf', '.json')
    with open(output_json_path, "w") as f:
        json.dump(posts, f, indent=2)
    print(f"JSON saved as {output_json_path}")


def main():
    args = parseargs()
    # Parse the start and end dates
    start_date = datetime.fromisoformat(args.start_date)
    end_date = datetime.fromisoformat(args.end_date)

    posts_file_path = os.path.expanduser(args.posts)
    edits_file_path = os.path.expanduser(args.edits)
    output_pdf_path = args.output

    # Load the JSON files
    posts = load_json_file(posts_file_path)
    edits = load_json_file(edits_file_path)

    # Filter posts by date range
    filtered_posts = filter_posts_by_date(posts, start_date, end_date)
    flattened_posts = flatten_post_data(filtered_posts)

    # Combine posts with edits
    combined_data = combine_posts_and_edits(flattened_posts, edits)

    # Generate PDF from the combined data
    generate_pdf_from_posts(combined_data, output_pdf_path)


if __name__ == "__main__":
    main()
