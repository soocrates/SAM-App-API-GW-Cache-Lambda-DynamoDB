import json
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('StockTable')

def lambda_handler(event, context):
    try:
        # Handle GET /stocks - only fetch latest version of each stock
        if event.get('resource') == '/stocks' and event.get('httpMethod') == 'GET':
            # First get all unique stock IDs
            stock_ids = set()
            scan_response = table.scan(
                ProjectionExpression='stockId',
                Limit=100
            )
            stock_ids.update(item['stockId'] for item in scan_response.get('Items', []))
            
            # Get only the latest version of each stock
            latest_stocks = []
            for stock_id in stock_ids:
                response = table.query(
                    KeyConditionExpression=Key('stockId').eq(stock_id),
                    Limit=1,
                    ScanIndexForward=False  # Get most recent first
                )
                if response.get('Items'):
                    latest_stocks.append(response['Items'][0])
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'max-age=300'  # 5 minutes
                },
                'body': json.dumps(_convert_decimals(latest_stocks))
            }
        
        # Handle GET /stocks/{stockId} - fetch all versions
        elif event.get('resource') == '/stocks/{stockId}' and event.get('httpMethod') == 'GET':
            stock_id = event.get('pathParameters', {}).get('stockId')
            if not stock_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'stockId is required'})
                }
            
            response = table.query(
                KeyConditionExpression=Key('stockId').eq(stock_id),
                Limit=100
            )
            
            items = response.get('Items', [])
            if not items:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': 'Stock not found'})
                }
                
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps(_convert_decimals(items))
            }
        
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Not found'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def _convert_decimals(data):
    """Recursively convert Decimal objects to float/int."""
    if isinstance(data, list):
        return [_convert_decimals(item) for item in data]
    elif isinstance(data, dict):
        return {k: _convert_decimals(v) for k, v in data.items()}
    elif isinstance(data, type(boto3.dynamodb.types.Decimal('0'))):
        return int(data) if data % 1 == 0 else float(data)
    return data