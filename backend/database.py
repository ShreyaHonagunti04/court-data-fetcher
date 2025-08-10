import os
from flask import current_app
from models import db, CaseQuery, CaseDetail, OrderJudgment
from datetime import datetime
import json

def init_database():
    """Initialize database tables"""
    with current_app.app_context():
        db.create_all()
        current_app.logger.info("Database tables created successfully")

def log_query(case_type, case_number, filing_year, success=False, 
              error_message=None, raw_response=None, parsed_data=None, ip_address=None):
    """Log a case query to the database"""
    try:
        query = CaseQuery(
            case_type=case_type,
            case_number=case_number,
            filing_year=filing_year,
            success=success,
            error_message=error_message,
            raw_response=raw_response,
            parsed_data=parsed_data,
            ip_address=ip_address
        )
        db.session.add(query)
        db.session.commit()
        return query.id
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error logging query: {str(e)}")
        return None

def save_case_details(case_data):
    """Save case details to database"""
    try:
        # Check if case already exists
        existing_case = CaseDetail.query.filter_by(case_id=case_data['case_id']).first()
        
        if existing_case:
            # Update existing record
            for key, value in case_data.items():
                if hasattr(existing_case, key):
                    setattr(existing_case, key, value)
            existing_case.last_updated = datetime.utcnow()
            case_detail = existing_case
        else:
            # Create new record
            case_detail = CaseDetail(**case_data)
            db.session.add(case_detail)
        
        db.session.commit()
        return case_detail.id
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving case details: {str(e)}")
        return None

def save_orders_judgments(case_detail_id, orders_data):
    """Save orders and judgments to database"""
    try:
        # Delete existing orders for this case
        OrderJudgment.query.filter_by(case_detail_id=case_detail_id).delete()
        
        # Add new orders
        for order_data in orders_data:
            order_data['case_detail_id'] = case_detail_id
            order = OrderJudgment(**order_data)
            db.session.add(order)
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving orders/judgments: {str(e)}")
        return False

def get_query_history(limit=100):
    """Get recent query history"""
    try:
        queries = CaseQuery.query.order_by(CaseQuery.query_timestamp.desc()).limit(limit).all()
        return [query.to_frontend_dict() for query in queries]
    except Exception as e:
        current_app.logger.error(f"Error fetching query history: {str(e)}")
        return []

def get_case_statistics():
    """Get database statistics"""
    try:
        stats = {
            'total_queries': CaseQuery.query.count(),
            'successful_queries': CaseQuery.query.filter_by(success=True).count(),
            'unique_cases': CaseDetail.query.count(),
            'total_orders': OrderJudgment.query.count()
        }
        return stats
    except Exception as e:
        current_app.logger.error(f"Error fetching statistics: {str(e)}")
        return {}