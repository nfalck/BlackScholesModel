# Black Scholes Options Risk Dashboard


A Streamlit application for option pricing, Greeks, implied volatility, and portfolio-level risk analysis using the Black Scholes model. The project combines live market data with scenario analysis and full portfolio repricing.
## Features

![image](images/demoimage.png)
- Retrieve live underlying price and risk-free rate from Yahoo Finance by selecting ticker
- Option to manually input underlying price, time and risk-free rate
- Choose strike price and volatility and retrieve call value, put value and greeks

![image](images/demoimage2.png)
- Choose market price and tolerance
- Calculate implied volatility and compare with your volatility

![image](images/portfoliodemo1.png)
- Upload an options portfolio from CSV or create the portfolio directly with the builder
- Retrieve live spot prices for the underlying assets
- Use maturity specific risk-free rates
- Derive contract specific implied volatility from live option chain prices

![image](images/portfoliodemo2.png)
- Calculate portfolio market value and aggregate Delta, Gamma, Vega, Theta and Rho
- Display a position-level breakdown of prices, market inputs, values and Greeks

![image](images/portfoliodemo3.png)
- Apply spot, volatility, interest rate and time-forward stress scenarios
- Compare Greek P&L approximation with full Black Scholes repricing

![image](images/portfoliodemo4.png)
- Break approximate scenario P&L into Delta, Gamma, Vega, Theta and Rho contributions

![image](images/portfoliodemo5.png)
- Visualize scenario exposure with an interactive Spot x Volatility P&L heatmap

## Demo


Try out the demo at: https://nfalckblackscholesmodel.streamlit.app/


## Run Locally


1. **Clone the Repository**: 
   - Open your terminal or command prompt.
   - Navigate to the directory where you want to clone the repository.
   - Run the following command:
     ```shell
     git clone https://github.com/nfalck/BlackScholesModel.git
     ```
     
2. **Install Dependencies**: 
   - You need to install streamlit, yfinance, numpy, matplotlib and scipy.
   - Install them separately or run the following command:
     ```shell
     pip install -r requirements.txt
     ```
     
2. **Run the Application**: 
   - Execute the following command to run the streamlit app:
     ```shell
     streamlit run main.py
     ```

## Resources


- [Code for Newton Raphson Method by QuantPy](https://www.youtube.com/watch?v=mPgVeazeq5U)
- Options, Futures and Other Derivatives by Hull and Basu