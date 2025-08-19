# Schedule Management System

A FastAPI-based schedule management system with user authentication, schedule management, and file sharing capabilities.

## Features

- User authentication (register/login)
- Schedule management with priorities
- File sharing and attachment support
- Real-time notifications
- Mobile-responsive design
- Priority-based color coding
- Schedule completion tracking
- User filtering
- File view mode

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd schedule-management-system
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python main.py
```

The application will be available at `http://localhost:8000`

## API Endpoints

### Authentication
- `POST /register` - Register a new user
- `POST /token` - Login and get access token
- `GET /users/me` - Get current user profile

### Schedules
- `GET /schedules/` - Get all schedules
- `POST /schedules/` - Create a new schedule
- `GET /schedules/{schedule_id}` - Get a specific schedule
- `PUT /schedules/{schedule_id}` - Update a schedule
- `DELETE /schedules/{schedule_id}` - Delete a schedule
- `POST /schedules/{schedule_id}/complete` - Mark a schedule as completed
- `POST /schedules/{schedule_id}/share` - Share a schedule with another user
- `POST /schedules/{schedule_id}/attachments` - Upload an attachment to a schedule

## Priority Levels

- 긴급 (Urgent) - Red background with blinking animation
- 급함 (High) - Orange background
- 곧임박 (Medium) - Yellow background
- 일반 (Low) - Green background
- 거북이 (Turtle) - Brown background

## File Sharing

The system supports sharing files through:
- Drag and drop interface
- File upload button
- Direct file sharing from other applications

## Security

- JWT-based authentication
- Password hashing with bcrypt
- CORS protection
- Input validation

## Development

To run the development server with auto-reload:
```bash
uvicorn main:app --reload
```

## Testing

Run tests with pytest:
```bash
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 