import csv
import io
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional, Union
from django import forms
from django.core.exceptions import ValidationError
@dataclass


class CSVColumnConfig:
    columns: List[str]
    validators: Dict[str, Callable[[str], bool]] = field(default_factory=dict)
    normalizers: Dict[str, Callable[[str], str]] = field(default_factory=dict)
    encoding: str = 'utf-8'
    custom_error_messages: Dict[str, str] = field(default_factory=dict)


def _normalize_column_config(config: Union[dict, CSVColumnConfig]) -> CSVColumnConfig:
    if isinstance(config, dict):
        return CSVColumnConfig(**config)
    return config


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Upload CSV File",
        widget=forms.ClearableFileInput(attrs={
            'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none',
            'accept': '.csv'
        }),
        help_text="Upload a CSV file"
    )
    def __init__(self, *args, column_config: Optional[Union[dict, CSVColumnConfig]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        if column_config:
            config = _normalize_column_config(column_config) if isinstance(column_config, dict) else column_config
            if config.columns:
                columns_text = ', '.join(config.columns)
                self.fields['csv_file'].help_text = f"Upload a CSV file with columns: {columns_text}"
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        if not csv_file.name.endswith('.csv'):
            raise ValidationError("File must be a CSV file.")
        if csv_file.size > 5 * 1024 * 1024:
            raise ValidationError("File size must be less than 5MB.")
        return csv_file


def parse_csv_data(csv_file, column_config: Union[dict, CSVColumnConfig]):
    config = _normalize_column_config(column_config)
    encoding = config.encoding
    required_columns = set(config.columns)
    validators = config.validators
    normalizers = config.normalizers
    custom_errors = config.custom_error_messages
    try:
        file_content = csv_file.read().decode(encoding)
        csv_file.seek(0)
        csv_reader = csv.DictReader(io.StringIO(file_content))
        if not required_columns.issubset(set(csv_reader.fieldnames)):
            missing = required_columns - set(csv_reader.fieldnames)
            found_columns = csv_reader.fieldnames if csv_reader.fieldnames else []
            error_msg = f"Missing required columns: {', '.join(sorted(missing))}\n"
            error_msg += f"Expected columns: {', '.join(sorted(required_columns))}\n"
            error_msg += f"Found columns: {', '.join(found_columns) if found_columns else 'None'}"
            raise ValidationError(error_msg)
        rows_data = []
        errors = []
        for row_num, row in enumerate(csv_reader, start=2):
            row_errors = []
            for field in required_columns:
                value = row.get(field, '').strip()
                if not value:
                    row_errors.append(f"'{field}' is required")
                    continue
                if field in validators:
                    validator = validators[field]
                    try:
                        if not validator(value):
                            error_msg = custom_errors.get(field, f"Invalid value for '{field}'")
                            row_errors.append(f"{error_msg} (value: '{value}')")
                    except Exception as e:
                        row_errors.append(f"Validation error for '{field}': {str(e)} (value: '{value}')")
            if row_errors:
                errors.append(f"Row {row_num}: {'; '.join(row_errors)}")
            else:
                clean_row = {'row_number': row_num}
                for field in required_columns:
                    value = row.get(field, '').strip()
                    if field in normalizers:
                        value = normalizers[field](value)
                    clean_row[field] = value
                rows_data.append(clean_row)
        if errors:
            max_errors_to_show = 10
            error_count = len(errors)
            if error_count > max_errors_to_show:
                errors_to_show = errors[:max_errors_to_show]
                errors_to_show.append(f"... and {error_count - max_errors_to_show} more errors")
            else:
                errors_to_show = errors
            raise ValidationError("CSV validation errors:\n" + "\n".join(errors_to_show))
        if not rows_data:
            raise ValidationError("No valid data found in CSV file.")
        return rows_data
    except csv.Error as e:
        raise ValidationError(f"Error reading CSV file: {str(e)}")
    except UnicodeDecodeError:
        raise ValidationError(f"File encoding error. Please ensure the file is {encoding} encoded.")


class UserImportReviewForm(forms.Form):
    confirm_import = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        }),
        label="I confirm that I want to import these users"
    )