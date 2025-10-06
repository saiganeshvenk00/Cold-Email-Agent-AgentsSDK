"""Cold outreach pipeline package (flattened)."""
from .workflow import run_cold_workflow, run_cold_workflow_bulk, load_recipients_from_csv
from .agents import sales_manager, email_manager, sales_picker
