from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class CaseQuery(db.Model):
    __tablename__ = 'case_queries'
    
    id = db.Column(db.Integer, primary_key=True)
    case_type = db.Column(db.String(100), nullable=False)
    case_number = db.Column(db.String(100), nullable=False)
    filing_year = db.Column(db.Integer, nullable=False)
    query_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)
    raw_response = db.Column(db.Text)
    parsed_data = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    
    def __repr__(self):
        return f'<CaseQuery {self.case_type}/{self.case_number}/{self.filing_year}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'case_type': self.case_type,
            'case_number': self.case_number,
            'filing_year': self.filing_year,
            'query_timestamp': self.query_timestamp.isoformat() if self.query_timestamp else None,
            'success': self.success,
            'error_message': self.error_message,
            'parsed_data': self.parsed_data
        }

    def to_frontend_dict(self):
        # For frontend history display
        return {
            'id': self.id,
            'case_type': self.case_type,
            'case_number': self.case_number,
            'filing_year': self.filing_year,
            'query_timestamp': self.query_timestamp.isoformat() if self.query_timestamp else None,
            'success': self.success,
            'error_message': self.error_message
        }

class CaseDetail(db.Model):
    __tablename__ = 'case_details'
    
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.String(200), unique=True, nullable=False)
    case_type = db.Column(db.String(100))
    case_number = db.Column(db.String(100))
    filing_year = db.Column(db.Integer)
    petitioner = db.Column(db.String(500))
    respondent = db.Column(db.String(500))
    filing_date = db.Column(db.Date)
    next_hearing_date = db.Column(db.Date)
    status = db.Column(db.String(200))
    stage = db.Column(db.String(200))
    court_name = db.Column(db.String(200))
    judge_name = db.Column(db.String(200))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'case_type': self.case_type,
            'case_number': self.case_number,
            'filing_year': self.filing_year,
            'petitioner': self.petitioner,
            'respondent': self.respondent,
            'filing_date': self.filing_date.isoformat() if self.filing_date else None,
            'next_hearing_date': self.next_hearing_date.isoformat() if self.next_hearing_date else None,
            'status': self.status,
            'stage': self.stage,
            'court_name': self.court_name,
            'judge_name': self.judge_name,
            'last_updated': self.last_updated.isoformat()
        }

class OrderJudgment(db.Model):
    __tablename__ = 'orders_judgments'
    
    id = db.Column(db.Integer, primary_key=True)
    case_detail_id = db.Column(db.Integer, db.ForeignKey('case_details.id'), nullable=False)
    order_date = db.Column(db.Date)
    order_type = db.Column(db.String(100))  # Order/Judgment
    description = db.Column(db.Text)
    pdf_url = db.Column(db.String(500))
    file_size = db.Column(db.String(50))
    
    case_detail = db.relationship('CaseDetail', backref=db.backref('orders_judgments', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'order_type': self.order_type,
            'description': self.description,
            'pdf_url': self.pdf_url,
            'file_size': self.file_size
        }