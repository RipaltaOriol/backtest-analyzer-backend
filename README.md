# Trade Sharpener: Server
*Formally known as Backtest Analyzer*

Trade Sharpener is an online, fully customizable trading journal with a focus on data analysis and optimization. Its purpose is to empower traders and enable them to quantify and enhance their trading strategies by taking control of their data.

The application consists of three modules: a non-relational database, an API server, and a client interface. The client obtains information from the backend via diverse API calls and makes use of the cache to prevent redundant requests, thereby enhancing its performance and reliability.
Once the user uploads their data to Trade Sharpener through one of the multiple supported methods, the server discerns this information and runs a series of pipelines and validation filters. This process ensures the data is stored in a uniform structure. Therefore, allowing information to be easily compared, contrasted, and modified if necessary.

Moreover, Trade Sharpener provides users with several features to support them in their analysis, including smart filters, note-taking capabilities, template selection, detailed statistics, and a comprehensive array of graphs for data visualization.

## Stack:
-	Python 3.8
-	Flask (Python framework)
-	NoSQL
-	Mongoengine (NoSQL ORM for Python)
-	Pandas
-	JWT
-	FPDF2
-	Matplotlib
-	Black (formatter)
-	GHA (CI/CD)
