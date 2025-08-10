import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, date
import time
import logging
from urllib.parse import urljoin, urlparse
import json

class DelhiHighCourtScraper:
    def __init__(self):
        import random
        self.base_url = "https://delhihighcourt.nic.in"
        self.search_url = f"{self.base_url}/case_status.asp"
        self.session = requests.Session()
        self.user_agents = [
            # List of common user agents
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        ]
        self.default_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.logger = logging.getLogger(__name__)
        self.random = random

    def get_case_types(self):
        """Get available case types from the court website"""
        case_types = [
            "CRL.A.", "CRL.REV.P.", "CRL.M.C.", "W.P.(C)", "W.P.(CRL)",
            "CM(M)", "LPA", "CS(OS)", "CS(COMM)", "FAO", "RFA", "MAC.APP",
            "CRL.L.P.", "ARB.P.", "CONT.CAS(C)", "BAIL APPLN."
        ]
        return case_types

    def search_case(self, case_type, case_number, filing_year, max_retries=3):
        """
        Search for a case on Delhi High Court website, with anti-bot evasion.
        """
        import time
        self.logger.info(f"Starting search for {case_type}/{case_number}/{filing_year}")
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                # Rotate user-agent
                user_agent = self.random.choice(self.user_agents)
                headers = self.default_headers.copy()
                headers['User-Agent'] = user_agent
                self.session.headers.update(headers)
                # Random delay to mimic human
                delay = self.random.uniform(1.5, 4.0)
                self.logger.info(f"[AntiBot] Sleeping for {delay:.2f}s before request (attempt {attempt})")
                time.sleep(delay)
                # Get the search page
                search_page = self.session.get(self.search_url, timeout=30)
                search_page.raise_for_status()
                soup = BeautifulSoup(search_page.content, 'html.parser')
                # Detect block/captcha page
                if self._is_blocked_page(soup):
                    self.logger.warning("Blocked or captcha page detected on GET. Retrying...")
                    raise Exception("Blocked or captcha page detected.")
                # Extract viewstate and other hidden fields if present
                viewstate = self._extract_viewstate(soup)
                # Prepare search parameters
                search_params = {
                    'case_type': case_type,
                    'case_no': case_number,
                    'case_year': str(filing_year),
                    'submit': 'Submit'
                }
                if viewstate:
                    search_params.update(viewstate)
                # Random delay before POST
                delay = self.random.uniform(1.0, 3.0)
                self.logger.info(f"[AntiBot] Sleeping for {delay:.2f}s before POST request (attempt {attempt})")
                time.sleep(delay)
                # Perform the search
                response = self.session.post(
                    self.search_url,
                    data=search_params,
                    timeout=30,
                    allow_redirects=True
                )
                response.raise_for_status()
                soup_post = BeautifulSoup(response.content, 'html.parser')
                if self._is_blocked_page(soup_post):
                    self.logger.warning("Blocked or captcha page detected on POST. Retrying...")
                    raise Exception("Blocked or captcha page detected.")
                # Parse the response
                result = self._parse_case_details(response.text, case_type, case_number, filing_year)
                # Ensure all dates are stringified for JSON compatibility
                if 'case_details' in result:
                    for k in ['filing_date', 'next_hearing_date']:
                        if k in result['case_details'] and isinstance(result['case_details'][k], (datetime, date)):
                            result['case_details'][k] = result['case_details'][k].isoformat()
                if 'orders_judgments' in result:
                    for order in result['orders_judgments']:
                        if 'order_date' in order and isinstance(order['order_date'], (datetime, date)):
                            order['order_date'] = order['order_date'].isoformat()
                self.logger.info(f"Search completed for {case_type}/{case_number}/{filing_year}")
                # Add query timestamp for frontend history display
                result['query_timestamp'] = datetime.now().isoformat()
                return result
            except Exception as e:
                last_exception = e
                self.logger.error(f"Attempt {attempt} failed: {str(e)}")
                # Exponential backoff
                if attempt < max_retries:
                    backoff = self.random.uniform(2, 5) * attempt
                    self.logger.info(f"[AntiBot] Backing off for {backoff:.2f}s before retry...")
                    time.sleep(backoff)
        # If all attempts fail
        if isinstance(last_exception, requests.RequestException):
            self.logger.error(f"Network error during case search: {str(last_exception)}")
            raise Exception("Network error: Unable to connect to court website")
        else:
            self.logger.error(f"Error searching case: {str(last_exception)}")
            raise Exception("Failed to fetch or parse case details. The court website may have changed, is unavailable, or anti-bot measures are blocking access.")

    def _is_blocked_page(self, soup):
        """Detect if the page is a block/captcha page"""
        block_indicators = [
            'captcha', 'verify you are human', 'access denied', 'blocked', 'unusual traffic',
            'please enable cookies', 'security check', 'robot', 'forbidden', 'not allowed'
        ]
        text = soup.get_text().lower()
        return any(indicator in text for indicator in block_indicators)

    def _extract_viewstate(self, soup):
        """Extract ASP.NET viewstate and other hidden fields"""
        viewstate_data = {}
        
        # Common ASP.NET hidden fields
        hidden_fields = ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']
        
        for field in hidden_fields:
            element = soup.find('input', {'name': field})
            if element and element.get('value'):
                viewstate_data[field] = element['value']
        
        return viewstate_data

    def _parse_case_details(self, html_content, case_type, case_number, filing_year):
        """Parse case details from the HTML response"""
        soup = BeautifulSoup(html_content, 'html.parser')
        # Check for "No records found" or similar messages
        if self._is_no_results(soup, html_content):
            self.logger.warning("No results found for the given case details.")
            raise Exception("Case not found. Please verify the case details.")
        try:
            case_data = {
                'case_id': f"{case_type}/{case_number}/{filing_year}",
                'case_type': case_type,
                'case_number': case_number,
                'filing_year': filing_year,
                'court_name': 'Delhi High Court'
            }
            # Extract case information using multiple strategies
            case_data.update(self._extract_parties(soup))
            case_data.update(self._extract_dates(soup))
            case_data.update(self._extract_status_info(soup))
            case_data.update(self._extract_judge_info(soup))
            # Extract orders and judgments
            orders = self._extract_orders_judgments(soup)
            # Stringify any date objects for JSON compatibility
            for k in ['filing_date', 'next_hearing_date']:
                if k in case_data and isinstance(case_data[k], (datetime, date)):
                    case_data[k] = case_data[k].isoformat()
            for order in orders:
                if 'order_date' in order and isinstance(order['order_date'], (datetime, date)):
                    order['order_date'] = order['order_date'].isoformat()
            return {
                'case_details': case_data,
                'orders_judgments': orders,
                'raw_html': html_content[:5000]  # Store first 5000 chars for debugging
            }
        except Exception as e:
            self.logger.error(f"Error parsing case details: {str(e)}")
            # Return partial data if parsing fails
            return {
                'case_details': {
                    'case_id': f"{case_type}/{case_number}/{filing_year}",
                    'case_type': case_type,
                    'case_number': case_number,
                    'filing_year': filing_year,
                    'court_name': 'Delhi High Court',
                    'status': 'Data extraction failed',
                    'parsing_error': str(e)
                },
                'orders_judgments': [],
                'raw_html': html_content[:5000]
            }

    def _is_no_results(self, soup, html_content):
        """Check if the response indicates no results found"""
        no_result_indicators = [
            "no records found",
            "case not found",
            "no matching records",
            "invalid case number",
            "case does not exist"
        ]
        
        content_lower = html_content.lower()
        return any(indicator in content_lower for indicator in no_result_indicators)

    def _extract_parties(self, soup):
        """Extract petitioner and respondent information"""
        parties_data = {}
        
        # Strategy 1: Look for standard table structure
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    if 'petitioner' in label or 'appellant' in label:
                        parties_data['petitioner'] = value
                    elif 'respondent' in label:
                        parties_data['respondent'] = value
        
        # Strategy 2: Look for specific patterns in text
        text_content = soup.get_text()
        
        # Pattern for "Petitioner vs Respondent"
        vs_pattern = r'([^v]+)\s+v[s]?\.\s+([^v]+)'
        vs_match = re.search(vs_pattern, text_content, re.IGNORECASE)
        if vs_match and not parties_data.get('petitioner'):
            parties_data['petitioner'] = vs_match.group(1).strip()
            parties_data['respondent'] = vs_match.group(2).strip()
        
        return parties_data

    def _extract_dates(self, soup):
        """Extract filing date and next hearing date"""
        dates_data = {}
        
        # Look for date patterns in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    if 'filing' in label or 'registration' in label:
                        dates_data['filing_date'] = self._parse_date(value)
                    elif 'next' in label and 'hearing' in label:
                        dates_data['next_hearing_date'] = self._parse_date(value)
                    elif 'hearing' in label and not dates_data.get('next_hearing_date'):
                        dates_data['next_hearing_date'] = self._parse_date(value)
        
        return dates_data

    def _extract_status_info(self, soup):
        """Extract case status and stage information"""
        status_data = {}
        
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    if 'status' in label:
                        status_data['status'] = value
                    elif 'stage' in label:
                        status_data['stage'] = value
        
        return status_data

    def _extract_judge_info(self, soup):
        """Extract judge information"""
        judge_data = {}
        
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    if 'judge' in label or 'coram' in label:
                        judge_data['judge_name'] = value
        
        return judge_data

    def _extract_orders_judgments(self, soup):
        """Extract orders and judgments with PDF links"""
        orders = []
        
        # Look for links to PDF files
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf', re.IGNORECASE))
        
        for link in pdf_links:
            href = link.get('href')
            if href:
                # Make URL absolute
                if href.startswith('/'):
                    pdf_url = self.base_url + href
                elif not href.startswith('http'):
                    pdf_url = urljoin(self.base_url, href)
                else:
                    pdf_url = href
                
                # Extract order information
                link_text = link.get_text(strip=True)
                parent_text = link.parent.get_text(strip=True) if link.parent else ""
                
                order_data = {
                    'order_type': self._determine_order_type(link_text, parent_text),
                    'description': link_text or "Court Document",
                    'pdf_url': pdf_url,
                    'order_date': self._extract_date_from_text(parent_text)
                }
                
                orders.append(order_data)
        
        # If no PDF links found, look for order information in tables
        if not orders:
            orders = self._extract_orders_from_tables(soup)
        
        return orders

    def _extract_orders_from_tables(self, soup):
        """Extract order information from table structures"""
        orders = []
        
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:  # Assuming date, type, description columns
                    row_text = row.get_text(strip=True).lower()
                    if any(keyword in row_text for keyword in ['order', 'judgment', 'disposed', 'hearing']):
                        order_data = {
                            'order_date': self._parse_date(cells[0].get_text(strip=True)),
                            'order_type': 'Order',
                            'description': ' '.join(cell.get_text(strip=True) for cell in cells[1:]),
                            'pdf_url': None
                        }
                        orders.append(order_data)
        
        return orders

    def _determine_order_type(self, link_text, context_text):
        """Determine if the document is an order or judgment"""
        combined_text = f"{link_text} {context_text}".lower()
        
        if 'judgment' in combined_text or 'judgement' in combined_text:
            return 'Judgment'
        elif 'order' in combined_text:
            return 'Order'
        else:
            return 'Document'

    def _extract_date_from_text(self, text):
        """Extract date from text using regex patterns"""
        if not text:
            return None
        
        # Common date patterns
        date_patterns = [
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b',  # DD/MM/YYYY or DD-MM-YYYY
            r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
            r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._parse_date(match.group(0))
        
        return None

    def _parse_date(self, date_str):
        """Parse date string into date object"""
        if not date_str or date_str.strip() == "":
            return None
        
        date_str = date_str.strip()
        
        # Common date formats
        date_formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
            "%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d",
            "%d %b %Y", "%d %B %Y",
            "%b %d, %Y", "%B %d, %Y"
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # If no format matches, try to extract year at least
        year_match = re.search(r'\b(20\d{2})\b', date_str)
        if year_match:
            try:
                return date(int(year_match.group(1)), 1, 1)
            except ValueError:
                pass
        
        return None

    def download_pdf(self, pdf_url, timeout=30):
        """Download PDF document"""
        try:
            response = self.session.get(pdf_url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            return {
                'content': response.content,
                'content_type': response.headers.get('content-type', 'application/pdf'),
                'filename': self._extract_filename_from_url(pdf_url)
            }
        except Exception as e:
            self.logger.error(f"Error downloading PDF: {str(e)}")
            raise Exception(f"Failed to download PDF: {str(e)}")

    def _extract_filename_from_url(self, url):
        """Extract filename from URL"""
        parsed_url = urlparse(url)
        filename = parsed_url.path.split('/')[-1]
        
        if not filename or not filename.endswith('.pdf'):
            filename = f"document_{int(time.time())}.pdf"
        
        return filename

# Alternative scraper for eCourts district courts

# Basic ECourtsScraper for Delhi District Courts

# ECourtsScraper for Faridabad District Court (Haryana)
class ECourtsScraper:
    def __init__(self):
        # Delhi High Court case status endpoint
        self.base_url = "https://delhihighcourt.nic.in/app/get-case-type-status"
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        # User agents for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        ]
        import random
        self.random = random

    def search_case(self, case_type, case_number, filing_year, max_retries=3):
        """
        Search for a case on Delhi High Court website using the new endpoint, with anti-bot evasion.
        """
        import time
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                # Rotate user-agent
                user_agent = self.random.choice(self.user_agents)
                # Realistic headers
                headers = {
                    'User-Agent': user_agent,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Referer': 'https://delhihighcourt.nic.in/',
                    'Origin': 'https://delhihighcourt.nic.in',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin',
                }
                # Random delay to mimic human
                delay = self.random.uniform(1.5, 4.0)
                self.logger.info(f"[AntiBot] Sleeping for {delay:.2f}s before request (attempt {attempt})")
                time.sleep(delay)
                # Get cookies by visiting the main page first
                try:
                    self.session.get('https://delhihighcourt.nic.in/', headers={'User-Agent': user_agent}, timeout=15)
                except Exception as e:
                    self.logger.warning(f"Could not fetch main page for cookies: {e}")
                # Prepare POST data
                data = {
                    "case_type": case_type,
                    "case_no": case_number,
                    "case_year": str(filing_year)
                }
                resp = self.session.post(self.base_url, json=data, headers=headers, timeout=30)
                resp.raise_for_status()
                # Log the full response to a file for debugging
                with open('delhihighcourt_response_debug.json', 'w', encoding='utf-8') as f:
                    f.write(resp.text)
                # Try to parse as JSON, fallback to raw text
                try:
                    result_json = resp.json()
                    case_details = self._parse_case_details(result_json, case_type, case_number, filing_year)
                    return {
                        'case_details': case_details,
                        'orders_judgments': [],
                        'raw_html': resp.text[:5000],
                        'query_timestamp': datetime.now().isoformat()
                    }
                except Exception as json_err:
                    self.logger.error(f"Response not JSON or unexpected format: {json_err}")
                    # Return raw response for debugging
                    return {
                        'case_details': {
                            'case_id': f"{case_type}/{case_number}/{filing_year}",
                            'case_type': case_type,
                            'case_number': case_number,
                            'filing_year': filing_year,
                            'court_name': 'Delhi High Court',
                            'status': 'Response not JSON or unexpected format',
                            'raw_response': resp.text[:1000]
                        },
                        'orders_judgments': [],
                        'raw_html': resp.text[:5000],
                        'query_timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                last_exception = e
                self.logger.error(f"Attempt {attempt} failed: {str(e)}")
                # Exponential backoff
                if attempt < max_retries:
                    backoff = self.random.uniform(2, 5) * attempt
                    self.logger.info(f"[AntiBot] Backing off for {backoff:.2f}s before retry...")
                    time.sleep(backoff)
        # If all attempts fail
        self.logger.error(f"Delhi High Court search error: {str(last_exception)}")
        raise Exception("Network error: Unable to connect to Delhi High Court portal or parse data.")

    def _parse_case_details(self, result_json, case_type, case_number, filing_year):
        # Minimal parser for the Delhi High Court JSON response
        # Adjust keys as per actual API response structure
        case_data = {
            'case_id': f"{case_type}/{case_number}/{filing_year}",
            'case_type': case_type,
            'case_number': case_number,
            'filing_year': filing_year,
            'court_name': 'Delhi High Court',
            'status': '-',
            'petitioner': '-',
            'respondent': '-',
            'judge_name': '-',
            'filing_date': '-',
            'next_hearing_date': '-',
        }
        # Try to extract info from JSON response
        try:
            # Example: result_json = { 'status': 'Pending', 'petitioner': '...', ... }
            if isinstance(result_json, dict):
                for key in case_data.keys():
                    if key in result_json and result_json[key]:
                        case_data[key] = result_json[key]
                # Try common alternative keys
                if 'petitioner' in result_json:
                    case_data['petitioner'] = result_json['petitioner']
                if 'respondent' in result_json:
                    case_data['respondent'] = result_json['respondent']
                if 'status' in result_json:
                    case_data['status'] = result_json['status']
                if 'judge' in result_json:
                    case_data['judge_name'] = result_json['judge']
                if 'filing_date' in result_json:
                    case_data['filing_date'] = result_json['filing_date']
                if 'next_hearing_date' in result_json:
                    case_data['next_hearing_date'] = result_json['next_hearing_date']
        except Exception as e:
            self.logger.error(f"Error parsing case details from JSON: {str(e)}")
        return case_data