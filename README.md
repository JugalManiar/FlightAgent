# Web Scraping for Flight Price Comparison

This project demonstrates web scraping techniques to extract flight data from three major Indian flight booking platforms: **MakeMyTrip**, **ClearTrip**, and **EaseMyTrip**. The extracted data is used to compare flight prices and provide the best options to users.

---

## What is Web Scraping?

Web scraping is the process of programmatically extracting data from websites. It involves accessing a webpage, parsing its content, and retrieving specific information, such as text, images, or structured data.

### Key Concepts:
- **HTML Parsing**: Extracting data from the structure of a webpage.
- **CSS Selectors**: Targeting specific elements on a webpage.
- **JavaScript Rendering**: Handling dynamic content loaded by JavaScript.
- **Browser Automation**: Simulating user interactions to access dynamic content.

---

## Tools and Libraries Used

- **Playwright**: For browser automation and handling dynamic content.
- **Asyncio**: For asynchronous execution of tasks.
- **JSON**: For storing and exporting scraped data.
- **Regular Expressions (Regex)**: For pattern matching and data extraction.

---

## How It Works

### 1. User Query
The user provides a natural language query, such as:
```
"Search for a flight from Mumbai to Delhi on 5th March."
```

### 2. Query Parsing
The query is parsed to extract structured information:
- **From City**: Mumbai
- **To City**: Delhi
- **Date**: 2026-03-05

### 3. Web Scraping
The parsed query is used to scrape flight data from the following platforms:

#### MakeMyTrip
- **URL**: Constructed dynamically based on the query.
- **Data Extracted**:
  - Airline Name
  - Flight Code
  - Departure and Arrival Times
  - Price
  - Duration
  - Stops

#### ClearTrip
- **URL**: Constructed with airport codes and date.
- **Data Extracted**:
  - Similar to MakeMyTrip.
  - Additional handling for dynamic class names.

#### EaseMyTrip
- **URL**: Uses a unique format with city names and codes.
- **Data Extracted**:
  - Prices stored in element attributes.
  - Sequential IDs for flight details.

### 4. Data Aggregation
The scraped data is combined, duplicates are removed, and the cheapest flight is identified.

### 5. Output
The results are displayed in the console and saved to a JSON file:
```json
{
  "query": {
    "from_city": "Mumbai",
    "to_city": "Delhi",
    "departure_date": "2026-03-05"
  },
  "results": [
    {
      "airline": "IndiGo",
      "price": 3500,
      "departure_time": "08:00",
      "arrival_time": "10:30",
      "source": "MakeMyTrip"
    },
    {
      "airline": "Air India",
      "price": 4000,
      "departure_time": "09:00",
      "arrival_time": "11:30",
      "source": "ClearTrip"
    }
  ]
}
```

---

## Challenges and Solutions

### 1. Dynamic Content Loading
- **Challenge**: Flight data is loaded dynamically using JavaScript.
- **Solution**: Use Playwright to wait for specific elements to load.

### 2. Anti-Bot Detection
- **Challenge**: Websites block automated browsers.
- **Solution**:
  - Use realistic user-agent strings.
  - Disable automation flags.
  - Add delays between actions.

### 3. Changing Website Structures
- **Challenge**: Websites frequently update their HTML structure.
- **Solution**: Implement fallback strategies and use multiple CSS selectors.

---

## How to Run

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Script**:
   ```bash
   python main.py "Search for a flight from Mumbai to Delhi on 5th March."
   ```

3. **View Results**:
   - Console output.
   - JSON file: `flight_results.json`.

---

## Legal and Ethical Considerations

- Always check the website's `robots.txt` file and terms of service.
- Avoid overloading servers with frequent requests.
- Use the data responsibly and only for educational purposes.

---

## References

- [Playwright Documentation](https://playwright.dev/python)
- [CSS Selectors Guide](https://www.w3schools.com/cssref/css_selectors.asp)
- [Web Scraping Best Practices](https://www.scrapingbee.com/blog/web-scraping/)
