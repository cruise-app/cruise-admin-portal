# tester.py
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
from typing import Optional
import supabase
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import uvicorn
from fastapi.encoders import jsonable_encoder


load_dotenv()

app = FastAPI(title="Test Reports Admin System",
              description="API for managing test reports with image uploads",
              version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB configuration
MONGO_URI = "mongodb+srv://Nouryoussri:Nour2003@cluster0.wjrco.mongodb.net/test_reports?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client.test_reports
collection = db.test_report

# Test the connection
try:
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
    db = client.test_reports    # Access your test_reports database
except Exception as e:
    print(f"Connection failed: {e}")

# Supabase setup
supabase_client = supabase.create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

class TestReport(BaseModel):
    description: str
    screenshot_url: Optional[str] = None
    created_at: datetime = datetime.now()
    status: str = "open"
    tester_name: Optional[str] = None

@app.post("/reports", response_model=TestReport)
@app.post("/reports/", response_model=TestReport)
async def create_report(
    description: str = Form(...),
    bucket_name: str = Form("test-report-bucket"),
    tester_name: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    screenshot_url = None
    
    if file:
        try:
            file_contents = await file.read()
            file_path = f"test_screenshots/{datetime.now().timestamp()}_{file.filename}"
            res = supabase_client.storage.from_(bucket_name).upload(
                file_path,
                file_contents
            )
            screenshot_url = f"{os.getenv('SUPABASE_URL')}/storage/v1/object/public/{bucket_name}/{file_path}"
        except Exception as e:
            print(f"Supabase upload error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload image to {bucket_name}: {str(e)}"
            )
    report_data = {
        "description": description,
        "screenshot_url": screenshot_url,
        "created_at": datetime.now(),
        "status": "open",
        "tester_name": tester_name
    }
    try:
        result = collection.insert_one(report_data)
        report_data["id"] = str(result.inserted_id)
        return report_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create report: {str(e)}"
        )

@app.get("/")
async def root():
    return {
        "message": "Test Reports API is running!",
        "endpoints": {
            "docs": "/docs",
            "create_report": "/reports/ (POST)",
            "get_reports": "/reports/ (GET)",
            "update_status": "/reports/{id}/status (PUT)"
        }
    }


@app.put("/reports/{report_id}/status", response_model=TestReport)
@app.put("/reports/{report_id}/status/", response_model=TestReport)
async def update_status(report_id: str, status: str):
    if status not in ["open", "in_progress", "resolved"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid status value. Must be 'open', 'in_progress', or 'resolved'"
        )
    try:
        result = collection.update_one(
            {"_id": report_id},
            {"$set": {"status": status}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Report not found")
        report = collection.find_one({"_id": report_id})
        if report:
            report["id"] = str(report["_id"])
            del report["_id"]
        return report
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update report: {str(e)}"
        )

@app.get("/reports")
@app.get("/reports/")
async def get_reports():
    try:
        reports = list(collection.find())
        for report in reports:
            report["id"] = str(report["_id"])
            del report["_id"]
        return jsonable_encoder(reports)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch reports: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)