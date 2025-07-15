"""
Excel Export Tool for creating training program spreadsheets
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class WorkoutDetail(BaseModel):
    """Details of a single workout."""

    day: str = Field(..., description="Day of the week (Monday, Tuesday, etc.)")
    title: str = Field(..., description="Title of the workout")
    duration: str = Field(..., description="Duration of the workout (e.g., '60 min')")
    description: str = Field(..., description="Description of the workout")
    type: str = Field(
        ..., description="Type of workout (Run, Bike, Swim, Strength, etc.)"
    )
    intensity: str = Field(..., description="Intensity level (Easy, Moderate, Hard)")


class ExcelExportParams(BaseModel):
    """Parameters for exporting a training program to Excel."""

    athlete_name: str = Field(..., description="Name of the athlete")
    week_start_date: str = Field(..., description="Start date of the week (YYYY-MM-DD)")
    workouts: List[WorkoutDetail] = Field(
        ..., description="List of workout details for the week"
    )
    notes: Optional[str] = Field(
        default=None, description="Additional notes for the training week"
    )


class ExcelExportTool(BaseTool):
    name: str = "export_training_plan_to_excel"
    description: str = "Creates an Excel spreadsheet with a weekly training program"
    args_schema: type[BaseModel] = ExcelExportParams

    def __init__(self):
        super().__init__()
        # Create output directory if it doesn't exist
        os.makedirs(os.path.join(os.getcwd(), "training_plans"), exist_ok=True)

    def _run(
        self,
        athlete_name: str,
        week_start_date: str,
        workouts: List[Dict[str, str]],
        notes: Optional[str] = None,
    ) -> str:
        """
        Creates an Excel file with the weekly training program.

        Args:
            athlete_name: Name of the athlete
            week_start_date: Start date of the week (YYYY-MM-DD)
            workouts: List of workout details for the week
            notes: Additional notes for the training week

        Returns:
            The path to the created Excel file
        """
        try:
            # Convert string date to datetime
            start_date = datetime.strptime(week_start_date, "%Y-%m-%d")
            week_end_date = datetime.strftime(
                datetime.strptime(week_start_date, "%Y-%m-%d").replace(
                    day=start_date.day + 6
                ),
                "%Y-%m-%d",
            )

            # Format date range for the filename
            date_range = f"{week_start_date}_to_{week_end_date}"

            # Create a DataFrame from the workouts
            df = pd.DataFrame(workouts)

            # Create a writer object
            file_name = (
                f"{athlete_name.replace(' ', '_')}_training_plan_{date_range}.xlsx"
            )
            file_path = os.path.join(os.getcwd(), "training_plans", file_name)

            # Create Excel writer using openpyxl
            writer = pd.ExcelWriter(file_path, engine="openpyxl")

            # Write the data to Excel
            df.to_excel(writer, sheet_name="Weekly Plan", index=False)

            # Access the workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets["Weekly Plan"]

            # Auto-adjust columns' width
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter

                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except Exception:
                        pass

                adjusted_width = max_length + 2
                worksheet.column_dimensions[column_letter].width = adjusted_width

            # Add notes section if provided
            if notes:
                # Create a new worksheet for notes
                notes_sheet = workbook.create_sheet(title="Notes")
                notes_sheet["A1"] = "Training Week Notes:"
                notes_sheet["A2"] = notes
                notes_sheet.column_dimensions["A"].width = 100

            # Add header with athlete name and date range
            header_sheet = workbook.create_sheet(title="Overview", index=0)
            header_sheet["A1"] = f"Training Plan for: {athlete_name}"
            header_sheet["A2"] = f"Week: {week_start_date} to {week_end_date}"
            header_sheet["A4"] = "Generated on: " + datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # Save the Excel file
            writer.close()

            return f"Training plan exported successfully to {file_path}"

        except Exception as e:
            return f"Error creating Excel export: {e}"
