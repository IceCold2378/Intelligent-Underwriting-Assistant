import asyncio
import httpx
import time

async def perform_test_analysis():
    async with httpx.AsyncClient() as client:
        # 1. Login to get token
        print("Logging in to get auth token...")
        login_res = await client.post(
            'http://localhost:8000/api/v1/auth/login', 
            json={'email': 'agent@example.com', 'password': 'password123'}
        )
        
        if login_res.status_code != 200:
            print("Failed to login:", login_res.text)
            return

        token = login_res.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}'}
        
        # 2. Create the test documents
        print("\nPreparing test applications...")
        
        doc1_content = """John Doe - Loan Application
Credit Score: 580
Annual Income: $60,000
Loan Amount: $400,000
DTI Ratio: 48%
LTV Ratio: 95%
Notes: Applicant has a recent history of late payments and one account in collections.
"""
        
        doc2_content = """Jane Smith - Loan Application
Credit Score: 810
Annual Income: $120,000
Loan Amount: $200,000
DTI Ratio: 25%
LTV Ratio: 60%
Notes: Excellent payment history, zero missed payments. High savings buffer.
"""
        
        with open('app1.txt', 'w') as f: f.write(doc1_content)
        with open('app2.txt', 'w') as f: f.write(doc2_content)
        
        # 3. Perform analysis 1 (High Risk)
        print("\nSubmitting Application 1 (John Doe - Low score, high DTI)...")
        start = time.time()
        files = {'file': ('app1.txt', open('app1.txt', 'rb'), 'text/plain')}
        res1 = await client.post('http://localhost:8000/api/v1/analysis', files=files, headers=headers, timeout=120.0)
        elapsed = time.time() - start
        
        if res1.status_code == 201:
            data = res1.json()['analysis']
            print(f"Success! Finished in {elapsed:.2f} seconds.")
            print(f"Risk Score: {data['overall_risk_score']} ({data['overall_risk_level'].upper()})")
            print(f"Recommendation: {data['recommendation']}")
            print(f"Summary: {data['summary'][:150]}...")
        else:
            print(f"Failed: {res1.status_code} {res1.text}")
            
        print("-" * 40)
        
        # 4. Perform analysis 2 (Low Risk)
        print("\nSubmitting Application 2 (Jane Smith - High score, low DTI)...")
        start = time.time()
        files = {'file': ('app2.txt', open('app2.txt', 'rb'), 'text/plain')}
        res2 = await client.post('http://localhost:8000/api/v1/analysis', files=files, headers=headers, timeout=120.0)
        elapsed = time.time() - start
        
        if res2.status_code == 201:
            data = res2.json()['analysis']
            print(f"Success! Finished in {elapsed:.2f} seconds.")
            print(f"Risk Score: {data['overall_risk_score']} ({data['overall_risk_level'].upper()})")
            print(f"Recommendation: {data['recommendation']}")
            print(f"Summary: {data['summary'][:150]}...")
            print(f"Details: {data['detailed_analysis'][:200]}")
        else:
            print(f"Failed: {res2.status_code} {res2.text}")

if __name__ == "__main__":
    asyncio.run(perform_test_analysis())
