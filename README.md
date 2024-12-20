# TP Scrap

## How to Run the Script

To run the script, you need to configure a `.env` file in the root directory of the project. This file should contain the database connection URL in the following format:

DATABASE_URL=postgres://user:password@host:port/database?sslmode=require

### Steps to Run:

1. Create a `.env` file in the root of your project directory.
2. Add the database connection URL as shown above.
3. Install the required Python dependencies using `pip`:
   pip install -r requirements.txt

4. Run the script:
   python script_name.py

Ensure the database credentials and URL are accurate to successfully insert the scrap
