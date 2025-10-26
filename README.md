# **Document Verification Portal**

This is a modern, persistent document verification application built using **Flask (Python)** for the backend and **MongoDB Atlas** for data storage. It allows a Teacher to set dynamic submission requirements (file type, keywords) and provide feedback on student submissions, which is then visible in the Student Portal.

## **🚀 1\. Prerequisites and Installation**

To run this application locally, you need the following software installed:

### **A. Core Software**

1. **Python 3.8+:** Download and install Python. Ensure you check the box to "Add Python to PATH" during installation.  
2. **Git:** (Recommended for managing code).  
3. **MongoDB Atlas Account:** A free account is sufficient. You will need to create a cluster and whitelist your IP address.

### **B. Project Setup**

1. **Clone the Repository:**  
   git clone \[your-repository-url\]  
   cd \[your-project-directory\]

2. Create a Virtual Environment:  
   A virtual environment isolates your project dependencies.  
   python \-m venv venv

3. **Activate the Environment:**  
   * **Windows:**  
     venv\\Scripts\\activate

   * **macOS/Linux:**  
     source venv/bin/activate

4. Install Dependencies:  
   You need Flask and several database/utility libraries.  
   pip install Flask python-dotenv pymongo werkzeug\[security\]

   *(Note: werkzeug\[security\] handles password hashing, and pymongo is the driver for MongoDB.)*

## **🔒 2\. Database and Environment Configuration**

This is the **most crucial step** for connecting to MongoDB Atlas and enabling email (OTP) functionality.

### **A. Create the .env File**

Create a new file named **.env** in the root directory of your project. Copy the template below and fill in your actual credentials.

**File: .env**

\# \-------------------------------------------------------------  
\# 1\. MONGODB ATLAS CONFIGURATION  
\# \-------------------------------------------------------------  
\# Replace the placeholder with your full MongoDB Atlas connection string.  
\# Ensure you URL-encode your username/password if they contain special characters.  
\# Example: mongodb+srv://user:pass@cluster.mongodb.net/doc\_verify?retryWrites=true\&w=majority  
MONGO\_URI="YOUR\_MONGODB\_ATLAS\_CONNECTION\_STRING"

\# \-------------------------------------------------------------  
\# 2\. APPLICATION SECURITY  
\# \-------------------------------------------------------------  
\# Must be a long, complex, random string.  
SECRET\_KEY="A\_VERY\_LONG\_AND\_SECURE\_RANDOM\_SECRET"

\# \-------------------------------------------------------------  
\# 3\. EMAIL CONFIGURATION (For Password Reset OTP)  
\# \-------------------------------------------------------------  
\# IMPORTANT: For Gmail, you must generate an "App Password"   
\# from your Google Account security settings, as standard passwords won't work.  
MAIL\_SERVER="smtp.gmail.com"  
MAIL\_PORT=587  
MAIL\_USERNAME="YOUR\_EMAIL\_ADDRESS\_FOR\_OTP"  
MAIL\_PASSWORD="YOUR\_APP\_PASSWORD\_OR\_SMTP\_PASSWORD"

### **B. MongoDB Atlas Preparation**

1. **Whitelist IP:** In your MongoDB Atlas Security settings, ensure your current public IP address is added to the Network Access list, or select "Allow access from anywhere" (less secure).  
2. **Database Name:** The application will automatically use the database named **doc\_verify** if the name is not explicitly included in your MONGO\_URI.

## **▶️ 3\. Running the Application**

1. **Ensure Environment is Active:** If you closed your terminal, reactivate the virtual environment: source venv/bin/activate (or venv\\Scripts\\activate on Windows).  
2. **Run the Flask App:**  
   python app.py

3. Access the Portal:  
   Open your web browser and navigate to:  
   \[http://127.0.0.1:5000/\](http://127.0.0.1:5000/)  
