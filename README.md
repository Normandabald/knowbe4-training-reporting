# KnowBe4 Training Reporting Tool

This tool generates training reports from the KnowBe4 API, including metrics and lists of untrained users for mandatory training campaigns.

## Features

- Fetches user data and training enrollments from the KnowBe4 API.
- Analyses training data to calculate metrics such as completion rates.
- Identifies users who have not completed mandatory training campaigns and their line managers.
- Generates CSV reports with training metrics and untrained user details.

## Requirements

- Python 3.11+
- Required Python packages (listed in `requirements.txt`):
  - pyyaml==6.0.2
  - requests==2.30.0
  - pandas==2.0.1

## Installation

1. Clone the repository:

   ```sh
   git clone https://github.com/yourusername/knowbe4-training-reporting.git
   cd knowbe4-training-reporting
   ```

2. Set up a virtual environment (optional but recommended):

   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required Python packages:

   ```sh
   pip install -r requirements.txt
   ```

## Configuration

1. Create a `config.yaml` file in the root directory with the following structure:

   ```yaml
   api:
     base_url: "https://eu.api.knowbe4.com/v1"
     api_key: "YOUR_API_KEY"

   training:
     mandatory_campaigns:
       - "Example Mandatory Training1"
       - "Example Mandatory Training2"
       - "Example Mandatory Training3"

   user_fields:
     optional:
       - "division"
       - "department"
   ```

2. Replace `YOUR_API_KEY` with your actual KnowBe4 API key.

## Usage

Run the tool to generate the training report:

```sh
python kb4_train.py
```

The tool will generate two CSV files in the current directory:

- `knowbe4_metrics_<timestamp>.csv`: Contains overall training metrics.
- `knowbe4_untrained_users_<timestamp>.csv`: Contains details of users who have not completed mandatory training.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
