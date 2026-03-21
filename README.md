# ClassBoard - Multi-College Academic Coordination Platform

A complete web application for managing academic information across multiple colleges.

## Features

### Core Modules
- **Authentication**: User registration, login, JWT-based authentication
- **User Management**: Role-based access control (Admin, CR, Student)
- **Academic Structure**: Colleges, Degrees, Branches, Sections
- **Announcements**: Create, view, filter announcements with tags
- **Assignments**: CR can create assignments and track student submissions
- **Reminders**: Personal and class reminders
- **Schedule Management**: Class timetable management

### User Roles
1. **Admin**: Manage users, academic structure, schedules
2. **CR (Class Representative)**: Create assignments, track submissions, announcements
3. **Student**: View assignments, announcements, reminders, schedule

---

## Project Structure

```
ClassBoard/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration
│   │   ├── database.py          # MongoDB connection
│   │   ├── models/              # MongoDB models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── routes/              # API endpoints
│   │   ├── auth/                # Authentication logic
│   │   ├── services/            # Business logic
│   │   └── utils/               # Utilities and dependencies
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/
    ├── src/
    │   ├── pages/               # Page components
    │   ├── components/          # Reusable components
    │   ├── layouts/             # Layout components
    │   ├── api/                 # API client
    │   ├── hooks/               # Custom hooks
    │   ├── store/               # Zustand store
    │   ├── App.jsx
    │   └── main.jsx
    ├── package.json
    ├── vite.config.js
    └── index.html
```

---

## Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- MongoDB 4.4+
- Git

---

## Installation & Setup

### 1. Install MongoDB

**On Windows:**
1. Download MongoDB Community Edition from https://www.mongodb.com/try/download/community
2. Run the installer and follow the setup wizard
3. MongoDB will be installed as a service and start automatically
4. Verify installation by opening command prompt and running:
   ```powershell
   mongod --version
   ```

**On macOS:**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**On Linux (Ubuntu):**
```bash
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl start mongod
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create .env file
copy .env.example .env

# Edit .env with your configuration (optional)
# Default MongoDB URL: mongodb://localhost:27017

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will start at: **http://localhost:8000**

API documentation will be available at: **http://localhost:8000/docs**

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend will start at: **http://localhost:5173**

---

## Database Initialization

The backend automatically creates the necessary MongoDB collections and indexes on startup.

### Create an Admin User (Manual Database Entry)

Connect to MongoDB and insert an admin user:

```javascript
// Using MongoDB shell
use classboard

db.users.insertOne({
  name: "Admin User",
  email: "admin@classboard.com",
  password_hash: "$2b$12$...", // Use bcrypt to hash your password
  role: "admin",
  college_id: null,
  degree_id: null,
  branch_id: null,
  year: null,
  section: null,
  created_at: new Date()
})
```

Or use Python to generate a hashed password:

```python
from app.auth.password import hash_password
password = "your_password"
hashed = hash_password(password)
print(hashed)
```

---

## API Endpoints

### Authentication
```
POST   /auth/register       - Register new student
POST   /auth/login          - Login user
GET    /auth/me             - Get current user
```

### Users (Admin only)
```
GET    /users               - Get all users
POST   /users               - Create new user
PUT    /users/{id}          - Update user
DELETE /users/{id}          - Delete user
POST   /users/{id}/assign-cr - Assign CR role
```

### Academic Structure (Admin only)
```
GET    /academic/colleges    - Get all colleges
POST   /academic/colleges    - Create college
GET    /academic/degrees     - Get all degrees
POST   /academic/degrees     - Create degree
GET    /academic/branches    - Get all branches
POST   /academic/branches    - Create branch
GET    /academic/sections    - Get all sections
POST   /academic/sections    - Create section
```

### Announcements
```
GET    /announcements        - Get all announcements
POST   /announcements        - Create announcement
GET    /announcements/{id}   - Get announcement details
DELETE /announcements/{id}   - Delete announcement
```

### Assignments
```
GET    /assignments          - Get all assignments
POST   /assignments          - Create assignment (CR only)
GET    /assignments/{id}     - Get assignment details
DELETE /assignments/{id}     - Delete assignment (CR only)
```

### Assignment Tracker (CR only)
```
GET    /assignments/{id}/tracker              - Get tracker
PUT    /assignments/{id}/tracker/{student_id} - Mark completed
```

### Reminders
```
GET    /reminders            - Get user reminders
POST   /reminders            - Create reminder
PUT    /reminders/{id}       - Update reminder
DELETE /reminders/{id}       - Delete reminder
```

### Schedule
```
GET    /schedule             - Get all schedules
GET    /schedule/{section_id} - Get section schedule
POST   /schedule             - Create schedule (Admin only)
```

---

## Using the Application

### 1. Register as a Student
- Click "Register" on the login page
- Fill in your details and select college, degree, branch, and year
- Click "Register"

### 2. Login
- Enter your email and password
- You'll be redirected to the dashboard

### 3. Student Dashboard
View your:
- Assignments
- Announcements
- Reminders
- Schedule
- Profile

### 4. Create a CR (Admin)
- Go to Admin Panel
- Find the student in the users list
- Click "Assign CR" to make them a Class Representative

### 5. CR Features
- Create and manage assignments
- Track student submissions
- Create announcements
- View schedule and reminders

### 6. Admin Features
- Manage users (create, edit, delete)
- Create academic hierarchy (colleges, degrees, branches, sections)
- Manage class schedules
- Assign CR roles

---

## Sample Data Generation Script

Create a Python script `populate_db.py` in the backend to populate initial data:

```python
import asyncio
from motor.motor_asyncio import AsyncClient
from app.auth.password import hash_password
from datetime import datetime, timezone

async def populate_db():
    client = AsyncClient("mongodb://localhost:27017")
    db = client["classboard"]
    
    # Admin user
    await db.users.insert_one({
        "name": "Admin",
        "email": "admin@example.com",
        "password_hash": hash_password("admin123"),
        "role": "admin",
        "created_at": datetime.now(timezone.utc)
    })
    
    # College
    college_result = await db.colleges.insert_one({
        "name": "ABC College of Engineering",
        "code": "ABC",
        "description": "Premier engineering college"
    })
    college_id = str(college_result.inserted_id)
    
    # Degree
    degree_result = await db.degrees.insert_one({
        "name": "Bachelor of Technology",
        "college_id": college_id,
        "code": "B.Tech"
    })
    degree_id = str(degree_result.inserted_id)
    
    # Branch
    branch_result = await db.branches.insert_one({
        "name": "Computer Science",
        "degree_id": degree_id,
        "code": "CSE"
    })
    branch_id = str(branch_result.inserted_id)
    
    # Section
    section_result = await db.sections.insert_one({
        "name": "CSE-A",
        "branch_id": branch_id,
        "year": 3
    })
    
    print("Sample data created successfully!")
    client.close()

asyncio.run(populate_db())
```

Run this script:
```bash
python populate_db.py
```

---

## Docker Setup (Optional)

Create a `docker-compose.yml` in the project root:

```yaml
version: '3.8'

services:
  mongodb:
    image: mongo:7.0
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URL=mongodb://mongodb:27017
      - DATABASE_NAME=classboard
    depends_on:
      - mongodb

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"

volumes:
  mongo_data:
```

Run with Docker:
```bash
docker-compose up
```

---

## Environment Variables

### Backend (.env)
```
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=classboard
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000
```

---

## Troubleshooting

### MongoDB Connection Error
- Ensure MongoDB is running: `mongod`
- Check MongoDB URL in `.env`
- Default URL: `mongodb://localhost:27017`

### Port Already in Use
- Backend (8000): `netstat -ano | findstr :8000`
- Frontend (5173): `netstat -ano | findstr :5173`
- Kill process: `taskkill /PID <PID> /F`

### Module Not Found Errors (Backend)
- Ensure virtual environment is activated
- Re-install dependencies: `pip install -r requirements.txt`

### CORS Errors (Frontend)
- Ensure backend is running on correct port (8000)
- Check CORS settings in `app/main.py`

### Dependencies Issues (Frontend)
- Clear node_modules: `rm -rf node_modules && npm install`
- Clear cache: `npm cache clean --force`

---

## Security Notes

1. **Change Secret Key**: Update `SECRET_KEY` in `.env` before production
2. **Password Hashing**: Uses bcrypt for secure password hashing
3. **JWT Tokens**: Use HTTPS in production
4. **CORS**: Configure allowed origins based on your deployment
5. **Admin Creation**: Admins cannot self-register; must be created by other admins or database entry

---

## Production Deployment

### Backend Deployment (Example with Heroku)
```bash
# Create Heroku app
heroku create classboard-backend

# Set environment variables
heroku config:set MONGODB_URL=... SECRET_KEY=...

# Deploy
git push heroku main
```

### Frontend Deployment (Example with Vercel)
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel
```

---

## Performance Optimization

1. **Database Indexes**: Already created on startup
2. **API Rate Limiting**: Consider adding rate limiting middleware
3. **Caching**: Implement Redis caching for frequently accessed data
4. **Pagination**: Add pagination to list endpoints
5. **File Storage**: Use cloud storage (S3) for attachments

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/AmazingFeature`
3. Commit changes: `git commit -m 'Add AmazingFeature'`
4. Push to branch: `git push origin feature/AmazingFeature`
5. Open a Pull Request

---

## License

This project is licensed under the MIT License.

---

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review API documentation at `/docs` (backend)
3. Check browser console for frontend errors
4. Review MongoDB logs

---

## Future Enhancements

- [ ] Real-time notifications with WebSockets
- [ ] File upload and attachment management
- [ ] Email notifications
- [ ] Mobile app (React Native)
- [ ] Assignment submission and grading
- [ ] Attendance tracking
- [ ] Class timetable conflicts detection
- [ ] Advanced analytics and reports
- [ ] Integration with calendar services
- [ ] Dark mode UI

---

**Last Updated**: March 2026
