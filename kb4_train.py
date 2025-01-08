import os
import csv
import logging
import json
from typing import List, Dict, Any

import yaml
import requests
import pandas as pd
import datetime
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KnowBe4ReportGenerator:
    def __init__(self, config_path: str = 'config.yaml'):
        
        # Load configuration from YAML file
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        # API Configuration
        self.api_key = self.config['api']['api_key']
        if not self.api_key:
            raise ValueError("API_KEY configuration is empty or invalid.")
        
        self.base_url = self.config['api']['base_url']
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Training configuration
        self.mandatory_campaigns = self.config['training']['mandatory_campaigns']
        logger.info(f"MANDATORY_CAMPAIGNS: {self.mandatory_campaigns}")
        if not self.mandatory_campaigns:
            logger.error("MANDATORY_CAMPAIGNS configuration is empty or invalid.")

        # Optional user fields configuration
        self.optional_user_fields = self.config['user_fields'].get('optional', [])
        logger.info(f"OPTIONAL_USER_FIELDS: {self.optional_user_fields}")

    def _paginated_get(self, endpoint: str, params: Dict[str, Any] = None) -> List[Dict]:
        """
        Paginated GET requests to KnowBe4 API
        
        Args:
            endpoint (str): API endpoint
            params (dict, optional): Additional query parameters

        Returns:
            list: Accumulated results from all pages
        """
        all_results = []
        page = 1
        per_page = 500  # Max allowed by API

        while True:
            request_params = params or {}
            request_params.update({
                'page': page,
                'per_page': per_page
            })

            try:
                response = requests.get(
                    f"{self.base_url}{endpoint}", 
                    headers=self.headers, 
                    params=request_params,
                    timeout=30
                )
                response.raise_for_status()
                
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response from {endpoint} in _paginated_get: {response.text}")
                    break
                
                if not data:
                    logger.error(f"Empty response from {endpoint} in _paginated_get: {response.text}")
                    break
                
                all_results.extend(data)
                
                if len(data) < per_page:
                    break
                
                page += 1
                
            except requests.RequestException as e:
                logger.error(f"Error fetching data from {endpoint} in _paginated_get: {e}")
                logger.error(f"Response content: {response.text}")
                break

        logger.info(f"Fetched {len(all_results)} items from {endpoint}")
        return all_results

    def get_users(self) -> List[Dict]:
        """
        Fetch all active users from KnowBe4
        
        Returns:
            list: User details
        """
        return self._paginated_get('/users', {'status': 'active'})

    def get_training_campaigns(self) -> List[Dict]:
        """
        Fetch training campaigns
        
        Returns:
            list: Campaign details
        """
        return self._paginated_get('/training/campaigns')

    def get_training_enrollments(self, campaign_id: int = None) -> List[Dict]:
        """
        Fetch training enrollments, optionally filtered by campaign
        
        Args:
            campaign_id (int, optional): Specific campaign to filter

        Returns:
            list: Training enrollment details
        """
        params = {'campaign_id': campaign_id} if campaign_id else {}
        return self._paginated_get('/training/enrollments', params)

    def analyse_training_data(self, users: List[Dict], enrollments: List[Dict], mandatory_campaigns: List[str]) -> Dict:
        """
        analyse training data and calculate metrics.
    
        Args:
            users (list): User details.
            enrollments (list): Training enrollments.
            mandatory_campaigns (list): List of mandatory campaign names.
    
        Returns:
            dict: Training metrics and untrained users.
        """
        # Create user lookup dictionary
        user_lookup = {user['id']: user for user in users}
        
        # Track untrained users
        untrained_users = set()
        user_enrollments = {}
    
        for enrollment in enrollments:
            user_id = enrollment['user']['id']
            campaign_name = enrollment['campaign_name']
            due_date = enrollment.get('due_date')
            status = enrollment.get('status')
            
            # Organise enrollments by user for mandatory campaign checks
            if user_id not in user_enrollments:
                user_enrollments[user_id] = []
            user_enrollments[user_id].append(enrollment)
            
            # Identify untrained users for mandatory campaigns
            if campaign_name in mandatory_campaigns:
                if status not in {'Completed', 'Passed'}:
                    if due_date:
                        due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M:%SZ')
                        if due_date < datetime.now():
                            untrained_users.add(user_id)
                    else:
                        untrained_users.add(user_id)
    
        untrained_user_data = [
            {
                'Name': f"{user_lookup[uid]['first_name']} {user_lookup[uid]['last_name']}",
                'Email': user_lookup[uid]['email'],
                'Manager': user_lookup[uid].get('manager_name', 'N/A'),
                **{field: user_lookup[uid].get(field, 'N/A') for field in self.optional_user_fields}
            }
            for uid in untrained_users if uid in user_lookup
        ]
    
        # Calculate overall metrics
        total_users = len(users)
        total_untrained = len(untrained_users)
        completion_rate = ((total_users - total_untrained) / total_users) * 100 if total_users else 0
    
        return {
            'metrics': {
                'Total Users': total_users,
                'Total Untrained Users': total_untrained,
                'Completion Rate (%)': round(completion_rate, 2),
            },
            'untrained_users': untrained_user_data,
    }


    def generate_report(self, output_dir: str = '.'):
        """
        Generate training report
        
        Args:
            output_dir (str): Where to save output files (default: current directory)
        """
        try:
            # Fetch data
            users = self.get_users()
            
            # Get relevant campaigns
            all_campaigns = self.get_training_campaigns()
            relevant_campaigns = [
                campaign for campaign in all_campaigns 
                if campaign['name'] in self.mandatory_campaigns
            ]
            logger.info(f"Found {len(relevant_campaigns)} relevant campaigns")

            # Fetch enrollments for each campaign
            all_enrollments = []
            for campaign in relevant_campaigns:
                campaign_enrollments = self.get_training_enrollments(campaign['campaign_id'])
                all_enrollments.extend(campaign_enrollments)

            report = self.analyse_training_data(users, all_enrollments, self.mandatory_campaigns)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            metrics_file = os.path.join(output_dir, f'knowbe4_metrics_{timestamp}.csv')
            untrained_file = os.path.join(output_dir, f'knowbe4_untrained_users_{timestamp}.csv')

            # Write metrics
            with open(metrics_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Metric', 'Value'])
                
                # Write overall metrics
                for key, value in report['metrics'].items():
                    if key != 'Division Completion Rates':
                        writer.writerow([key, value])
                    else:
                        writer.writerow(['Division Completion Rates', ''])
                        for div, rate in value.items():
                            writer.writerow([f' - {div}', rate])

            # Write untrained users
            if report['untrained_users']:
                pd.DataFrame(report['untrained_users']).to_csv(untrained_file, index=False)

            logger.info(f"Metrics saved to {metrics_file}")
            logger.info(f"Untrained users saved to {untrained_file}")

        except Exception as e:
            logger.error(f"An error occurred in generate_report: {e}", exc_info=True)

def main():
    try:
        generator = KnowBe4ReportGenerator()
        generator.generate_report()
    except Exception as e:
        logger.error(f"An error occurred in main: {e}")

if __name__ == '__main__':
    main()