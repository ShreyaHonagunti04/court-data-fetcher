import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import io

from scraper import ECourtsScraper

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize CORS
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)

# Sample case types for Delhi High Court
CASE_TYPES = [
    "CRL.A.", "CRL.REV.P.", "CRL.M.C.", "W.P.(C)", "W.P.(CRL)",
    "CM(M)", "LPA", "CS(OS)", "CS(COMM)", "FAO", "RFA", "MAC.APP",
    "CRL.L.P.", "ARB.P.", "CONT.CAS(C)", "BAIL APPLN."
]


# Database imports
from database import (
    log_query, save_case_details, save_orders_judgments, get_query_history, get_case_statistics
)


# Initialize the Delhi High Court scraper
scraper = ECourtsScraper()

@app.route('/')
def index():
    """Main application page"""
    current_year = datetime.now().year
    return render_template('index.html', case_types=CASE_TYPES, current_year=current_year)

@app.route('/api/case-types')
def get_case_types():
    """Get available case types"""
    try:
        return jsonify({
            'success': True,
            'case_types': CASE_TYPES
        })
    except Exception as e:
        app.logger.error(f"Error fetching case types: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch case types'
        }), 500

@app.route('/api/search', methods=['POST'])
def search_case():
    """Search for a case - Real implementation using database"""
    try:
        data = request.get_json()
        case_type = data.get('case_type', '').strip()
        case_number = data.get('case_number', '').strip()
        filing_year = data.get('filing_year')
        # Validation
        if not all([case_type, case_number, filing_year]):
            return jsonify({
                'success': False,
                'error': 'All fields (case type, case number, filing year) are required'
            }), 400
        try:
            filing_year = int(filing_year)
            if filing_year < 1950 or filing_year > datetime.now().year:
                raise ValueError("Invalid year")
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Please enter a valid filing year'
            }), 400
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        try:
            # Fetch real data using the new Delhi High Court scraper
            result = scraper.search_case(case_type, case_number, filing_year)
            # Save case details and orders to DB (if case_details is present)
            case_id = result['case_details'].get('case_id')
            case_detail_id = save_case_details(result['case_details']) if result.get('case_details') else None
            if case_detail_id and result.get('orders_judgments'):
                save_orders_judgments(case_detail_id, result['orders_judgments'])
            # Log query as successful if status is not error
            log_query(
                case_type=case_type,
                case_number=case_number,
                filing_year=filing_year,
                success=True if result['case_details'].get('status', '').lower() not in ['data extraction failed', 'response not json or unexpected format'] else False,
                error_message=None if result['case_details'].get('status', '').lower() not in ['data extraction failed', 'response not json or unexpected format'] else result['case_details'].get('status'),
                raw_response=result.get('raw_html'),
                parsed_data=result['case_details'],
                ip_address=client_ip
            )
            app.logger.info(f"Search successful: {case_id}")
            return jsonify({
                'success': True,
                'data': {
                    'case_details': result['case_details'],
                    'orders_judgments': result['orders_judgments']
                }
            })
        except Exception as search_error:
            error_message = str(search_error)
            app.logger.error(f"Search error: {error_message}")
            # Log query as failed
            log_query(
                case_type=case_type,
                case_number=case_number,
                filing_year=filing_year,
                success=False,
                error_message=error_message,
                raw_response=None,
                parsed_data=None,
                ip_address=client_ip
            )
            return jsonify({
                'success': False,
                'error': error_message
            }), 404
    except Exception as e:
        app.logger.error(f"Unexpected error in search_case: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred. Please try again later.'
        }), 500

@app.route('/api/download/<path:pdf_url>')
def download_pdf(pdf_url):
    """Download PDF document - Demo implementation"""
    try:
        # In real implementation, this would download from the actual URL
        # For demo, we'll create a simple PDF-like response
        demo_content = b"Demo PDF content - This would be the actual PDF file"
        
        pdf_file = io.BytesIO(demo_content)
        
        return send_file(
            pdf_file,
            as_attachment=True,
            download_name="demo_court_document.pdf",
            mimetype="application/pdf"
        )
        
    except Exception as e:
        app.logger.error(f"Error downloading PDF: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to download PDF document'
        }), 500

@app.route('/api/history')
def get_history():
    """Get search history from database"""
    try:
        limit = request.args.get('limit', 20, type=int)
        history = get_query_history(limit)
        return jsonify({
            'success': True,
            'data': history
        })
    except Exception as e:
        app.logger.error(f"Error fetching history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch search history'
        }), 500

@app.route('/api/stats')
def get_stats():
    """Get application statistics from database"""
    try:
        stats = get_case_statistics()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        app.logger.error(f"Error fetching stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch statistics'
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )