"""Generate sample resume and JD PDFs for testing."""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

fixtures_dir = "fixtures"

# Sample resume content
resume_content = [
    """JOHN SMITH
john.smith@email.com | +1-555-0123 | LinkedIn.com/in/johnsmith

EXPERIENCE
Senior Backend Engineer | TechCorp Inc | 2020-present
- Led development of microservices using FastAPI and Python
- Managed Postgres databases with 100M+ records
- Improved API response time by 40%

Backend Developer | StartupXYZ | 2018-2020
- Built REST APIs using Node.js and Express
- Implemented Redis caching layer
- Mentored 3 junior developers

EDUCATION
Bachelor of Science, Computer Science | State University | 2018

SKILLS
Python, FastAPI, PostgreSQL, Redis, Docker, Kubernetes, AWS, React
""",
    """JANE DOE
jane.doe@email.com | +1-555-0456 | github.com/janedoe

PROFESSIONAL SUMMARY
Full-stack engineer with 5+ years experience in cloud infrastructure and modern web development.

EXPERIENCE
Cloud Architecture Engineer | CloudSys | 2021-present
- Designed and deployed microservices on AWS ECS and EKS
- Automated infrastructure using Terraform and CloudFormation
- Reduced cloud costs by 35%

Software Engineer | WebDev Co | 2019-2021
- Developed React frontend and Python backend
- Implemented CI/CD pipelines with Jenkins
- Deployed applications to production weekly

EDUCATION
Master's in Computer Science | Tech Institute | 2019

SKILLS
AWS, Kubernetes, Docker, Python, React, Terraform, PostgreSQL, JavaScript
""",
    """ROBERT JOHNSON
robert@email.com | (555) 789-0123

EXPERIENCE
Principal Software Engineer | MegaTech | 2022-present
- Architect large-scale distributed systems
- Tech lead for 12-person engineering team
- Designed event streaming platform using Kafka

Senior Engineer | DataCorp | 2019-2022
- Built data pipeline processing 10GB+ daily
- Optimized database queries reducing latency 60%
- On-call engineer for critical systems

EDUCATION
BS Computer Science | University | 2015

SKILLS
Java, Python, Scala, Kubernetes, Cassandra, Kafka, GCP, Spark
"""
]

jd_content = [
    """Senior Backend Engineer

Company: TechVision Inc
Location: San Francisco, CA
Employment Type: Full-time

We are looking for a Senior Backend Engineer with 5+ years of experience.

Responsibilities:
- Design and implement scalable microservices
- Lead technical discussions and code reviews
- Mentor junior developers
- Participate in on-call rotation

Required Skills:
- Python and FastAPI
- PostgreSQL and Redis
- Docker and Kubernetes
- AWS or GCP
- RESTful API design

Compensation: 180,000 - 220,000 USD + benefits
""",
    """Full Stack Engineer

Company: InnovateTech
Location: Remote, USA
Employment Type: Full-time

Join our team to build modern web applications.

Responsibilities:
- Build responsive React frontends
- Develop Node.js/Python backends
- Deploy to AWS infrastructure
- Collaborate with product and design teams

Required Skills:
- React and JavaScript/TypeScript
- Node.js or Python
- AWS services (EC2, S3, RDS)
- SQL and NoSQL databases
- Git and CI/CD

Salary Range: 120,000 - 160,000 INR LPA
""",
    """DevOps Engineer

Company: CloudScale Systems
Location: Bangalore, India
Employment Type: Full-time

Build and maintain infrastructure for our growing platform.

Responsibilities:
- Manage Kubernetes clusters
- Implement Infrastructure as Code
- Monitor and optimize cloud resources
- Automate deployment pipelines

Required Skills:
- Kubernetes and Docker
- Terraform or CloudFormation
- Linux/Unix administration
- Python or Go scripting
- Experience with AWS/GCP/Azure

Compensation: 18-25 LPA + stock options
"""
]

def create_pdf(filename, text):
    """Create a simple PDF with text."""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    y = height - 40
    for line in text.split('\n'):
        if y < 40:
            c.showPage()
            y = height - 40
        c.drawString(40, y, line[:80] if len(line) > 80 else line)
        y -= 14
    
    c.save()

# Create resume PDFs
for i, content in enumerate(resume_content, 1):
    filename = os.path.join(fixtures_dir, f"resume_{i}.pdf")
    create_pdf(filename, content)
    print(f"✓ Created {filename}")

# Create JD PDFs
for i, content in enumerate(jd_content, 1):
    filename = os.path.join(fixtures_dir, f"jd_{i}.pdf")
    create_pdf(filename, content)
    print(f"✓ Created {filename}")

print("\nAll fixtures created successfully!")
