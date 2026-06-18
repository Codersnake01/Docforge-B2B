DocForge B2B API

API to generate PDF documents from dynamic HTML templates. Designed for B2B integrations.

Base URL: https://docforge-b2b-api.onrender.com

🔐 Authentication
Use an API Key in the X-API-Key header. (Example: -H "X-API-Key: YOUR_API_KEY")

Don't have an API Key?

Register your company with POST /api/v1/organizations.
Write to us at ondastudiolab@proton.me to get one.

📦 Plans & Limits
| Plan       | Price    | Documents/month |
|------------|----------|-----------------|
| FREE       | $0       | 50              |
| PRO        | $19/mo   | 5,000           |
| ENTERPRISE | $99/mo   | Unlimited       |

View plans and subscribe →

📚 Usage Examples
Company Registration
curl -X POST https://docforge-b2b-api.onrender.com/api/v1/organizations \
  -H "Content-Type: application/json" \
  -d '{"name": "My Company", "email": "email@example.com"}'

Create a Template
curl -X POST https://docforge-b2b-api.onrender.com/api/v1/templates \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "name": "Invoice",
    "html_content": "<html>...{{ var }}...</html>",
    "placeholders": "[\"var\"]"
  }'

Generate a PDF
curl -X POST https://docforge-b2b-api.onrender.com/api/v1/documents/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"template_id": 1, "data": {"var": "value"}}'

📬 Contact & Support
Developed by Onda Studio Lab. For inquiries, write to us at ondastudiolab@proton.me.

DocForge B2B · Interactive documentation at /docs
