import boto3
import random
import time
import os
from decimal import Decimal

def lambda_handler(event, context):
    """Lambda handler for stock data generation and cache invalidation"""
    # Initialize DynamoDB client
    table = boto3.resource('dynamodb').Table('StockTable')
    
    # Core stock symbols
    stocks = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
        'META', 'NVDA', 'PYPL', 'NFLX', 'ADBE'
    ]
    
    try:
        # Update stock prices
        update_stocks(table, stocks)
        
        # Invalidate cache
        invalidate_result = invalidate_cache()
        
        return {
            'statusCode': 200,
            'body': {
                'status': 'success',
                'updated': len(stocks),
                'cache_invalidated': invalidate_result,
                'timestamp': int(time.time())
            }
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {'statusCode': 500, 'body': {'error': str(e)}}

def update_stocks(table, stocks):
    """Update stock prices in DynamoDB"""
    now = int(time.time())
    expire_time = now + (30 * 86400)  # 30 days in seconds
    
    for symbol in stocks:
        # Get current price or use default
        current_price = get_price(table, symbol) or Decimal('100.00')
        
        # Calculate new price (±5% volatility)
        change = Decimal(str(random.uniform(-0.05, 0.05) * float(current_price)))
        new_price = round(max(Decimal('10'), current_price + change), 2)
        
        # Save to DynamoDB
        table.put_item(Item={
            'stockId': symbol,
            'timestamp': now,
            'price': new_price,
            'expireAt': expire_time
        })
        
        print(f"Updated {symbol}: {current_price} → {new_price}")

def get_price(table, symbol):
    """Get latest price for a stock"""
    try:
        response = table.query(
            KeyConditionExpression='stockId = :sid',
            ExpressionAttributeValues={':sid': symbol},
            ScanIndexForward=False,
            Limit=1
        )
        if response['Items']:
            return response['Items'][0]['price']
        return None
    except Exception as e:
        print(f"Error getting price for {symbol}: {e}")
        return None

def invalidate_cache():
    """Invalidate API Gateway cache"""
    api_id = os.environ.get('API_ID')
    stage = os.environ.get('STAGE_NAME')
    
    if not api_id or not stage:
        print("API_ID or STAGE_NAME not set")
        return False
    
    try:
        boto3.client('apigateway').flush_stage_cache(
            restApiId=api_id,
            stageName=stage
        )
        print(f"Invalidated cache for API {api_id}")
        return True
    except Exception as e:
        print(f"Cache invalidation error: {e}")
        return False