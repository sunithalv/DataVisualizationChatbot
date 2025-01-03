from langchain import hub
from langchain.prompts import SystemMessagePromptTemplate
from langchain.prompts import PromptTemplate

def get_prompt_template():
    query_prompt_template = hub.pull("langchain-ai/sql-query-system-prompt")
    current_template=query_prompt_template.messages[0].prompt.template
    # Modifying existing template to add specific instructions for a column
    new_template = f"""
    {current_template}

    Additional Instructions:
    - For getting count of t shirts always refer column 'stock_quantity' of 't_shirts' table. If multiple rows are returned calculate sum of column 'stock_quantity' for rows instead of counting the rows returned.
    - If distribution count is asked for plots no need to check 'discounts' table.
    - For getting the price of t shirts always follow the following steps:
    1. The 'price' column of 't_shirts' table indicates the base price of one t shirt only.
    2. Next,Always check in the 'discounts' table if any entry exists for given t shirt id.
    3. If entry exists 'pct_discount' column in that row refers to the discount percentage for a given t shirt id.
    Calculate discounted price as price*(1-(pct_discount/100)).Else ignore the 'discounts' table.
    - If distribution of discount percentages return the pct_discount vales with corresponding stock_quantity.
    - If distribution of prices is asked, return the discounted prices (if discount is applicable else original price) along with the corresponding stock_quantity
    - If plot of column A vs column B is asked, return results only with columns 'A' and 'B' data when values in both A and B exists. 
    Note: for plot of discounts vs prices since it is to identify the trend in discount, return pct_discount and price column value without applying the discount when values exists in both columns.

    """

    # Create a new SystemMessagePromptTemplate with the updated template
    updated_message = SystemMessagePromptTemplate(
        prompt=query_prompt_template.messages[0].prompt.copy(update={"template": new_template})
    )

    # Replace the old message with the updated one
    query_prompt_template.messages[0] = updated_message

    return query_prompt_template

def create_data_transform_prompt(chart_type,result,question):
        base_prompt = """You are a data transformation expert. Transform the SQL query result into the exact format needed for a {chart_type} chart.

          SQL Query Result: {result}

          Your response must be a valid JSON object containing ONLY the chart_data field with the exact structure shown in the example.
          Do not include the term 'metric name'in result and always replace it with the actual name from the SQL query result labels.
          Ensure:
            1. Labels include all unique categories (e.g., sizes like XS, S, M, L, XL) from the SQL data.
            2. Data points for each metric are filled for all labels. If a metric has no value for a category, use 0.
            3. All metrics (e.g., Black, Red, White, Blue) are represented as separate "label" entries with their corresponding counts.
            4. Refer the {question} as the context for transforming data for required plots and populate the field 'title' with the actual title for the chart based on context
        """

        chart_prompts = {
            "bar": """For a bar chart, return JSON in this EXACT format:
              {{
                  "chart_data": {{
                      "labels": ["Category1", "Category2", ...],
                      "values": [
                          {{
                              "data": [number1, number2, ...],
                              "label": "Metric Name"
                          }}
                      ],
                        "title": "Chart Title",
                        'x_label': 'Dynamic X-Axis Label'
                  }}
              }}

              Example: 
              {{
                  "chart_data": {{
                      "labels": ["brand A", "brand B", "brand C"],
                      "values": [
                          {{
                              "data": [45, 32, 28],
                              "label": "T shirt Count"
                          }}
                      ],
                        "title": "T shirt Count by Brand",
                        'x_label': 'Brands'
                  }}
              }}""",

            "stacked bar": """For a stacked bar chart, follow these steps:
            Instructions:
            1. Identify all unique values from the x-axis category values (e.g., sizes) and form a list in their natural order.
            2. Extract unique values from the stack category column (e.g., colors). Each unique value becomes a `stack_category` in `stack_groups`.
            3. Create a dictionary for each stack category with corresponding counts corresponding to category position in x-axis categories as counts list.
            4. To populate the `counts` list ,for each stack category follow the steps below:
                - For each stack category,iterate over the x-axis category array to get stack category,x-axis category pair.
                - In the input data search for tuple with matching stack category,x-axis category pair and get corresponding count from tuple.
                  For eg. for stack category "Black" and x-axis category "XS" , find entry ('Black', 'XS', 100) in input data and get the value as 100.   
                - If tuple not found, use 0 as count.
                - The identified counts value should be entered in the counts list at position corresponding to x-axis category position.
            Follow the above instructions to return JSON in this EXACT format:
              {{
                  "chart_data": {{
                      "x_axis_categories": ["X axis Category 1", "X axis Category 2", ...],
                      "stack_groups": [
                          {{
                              "counts": [number1, number2, ...],
                              "stack_category": "Stack Category 1"
                          }},
                          {{
                              "counts": [number1, number2, ...],
                              "stack_category": "Stack Category 2"
                          }}
                          ...
                      ],
                        "title": "Chart Title",
                        'x_label': 'Dynamic X-Axis Label',
                        'y_label': 'Dynamic Y-Axis Label'
                  }}
              }}

              **Example**:  
                Input:  
                [
                ("Segment 1", "Category A", 10),
                ("Segment 2", "Category A", 15),
                ("Segment 1", "Category B", 20),
                ("Segment 2", "Category C", 10)
                ]

                Output:  
                {{
                    "chart_data": {{
                        "x_axis_categories": ["Category A", "Category B","Category C"],
                        "stack_groups": [
                            {{ "counts": [10, 20,0], "stack_category": "Segment 1" }},
                            {{ "counts": [15, 0,10], "stack_category": "Segment 2" }}
                        ],
                        "title": "Category Distribution by Segment",
                        'x_label': 'Categories',
                        'y_label': 'T shirt Count'
                    }}
                }}
              """,

            "pie": """For a pie chart, return JSON in this EXACT format:
              {{
                  "chart_data": {{
                  [
                      {{
                          "value": number,
                          "label": "Category Name",
                      }},
                      ...,

                  ],
                  'title': "Chart Title"
                  }}
              }}

              Example:
              {{
                  "chart_data": {{
                  [
                      {{
                          "value": 15,
                          "label": "Brand A"
                      }},
                      {{
                          "value": 45,
                          "label": "Brand B"
                      }},
                      {{
                          "value": 25,
                          "label": "Brand C"
                      }}
                  ],
                    'title': "Brand Distribution
                  }}
              }}""",
            "histogram": """For a histogram, return JSON in this EXACT format:
              {{
                  "chart_data": {{
                      "bins": [number1, number2, ...],
                      "counts": [count1, count2, ...],
                      "x_label": "X-axis Label",
                      "y_label": "Frequency",
                      'title': "Chart Title"
                  }}
              }}

               Example with SQL: "SELECT d.pct_discount FROM t_shirts t INNER JOIN discounts d ON t.tshirt_id = d.tshirt_id"
              {{
                  "chart_data": {{
                      "bins": [0, 10, 20, 30, 40, 50],
                      "counts": [10, 15, 20, 25, 30],
                      "x_label": "Discount Percentage (%)",
                      "y_label": "Frequency",
                      'title': "Distribution of discount percentages"
                  }}
              }}
             """,


            "scatter": """For a scatter plot, return JSON in this EXACT format:
              {{
                  "chart_data": {{
                      "data_points": [
                          {{
                              "x": number1,
                              "y": number2
                          }},
                          {{
                              "x": number3,
                              "y": number4
                          }},
                          ...
                      ],
                      "x_label": "X-axis Label",
                      "y_label": "Y-axis Label",
                      'title': "Chart Title"
                  }}
              }}

              Example with SQL: "SELECT price, stock_quantity FROM t_shirts"
              {{
                  "chart_data": {{
                      "data_points": [
                          {{
                              "x": 10,
                              "y": 150
                          }},
                          {{
                              "x": 20,
                              "y": 120
                          }},
                          {{
                              "x": 30,
                              "y": 90
                          }}
                      ],
                      "x_label": "Price ($)",
                      "y_label": "Stock Quantity",
                      'title': "Price vs Stock Quantity"
                  }}
              }}
             """
        }

        return PromptTemplate.from_template(base_prompt + chart_prompts.get(chart_type))


def get_viz_prompt():
    viz_prompt = PromptTemplate.from_template("""
    You are an AI assistant that recommends appropriate data visualizations for price,count,size,colour,brand distribution and analysis for t shirts in a store.
    Based on the user's question, SQL query, and query results, suggest the most suitable type of graph or chart to visualize the data.

    Available chart types and their best use cases:

    - Bar Graphs (for 3+ categories): 
    * Comparing distributions or counts across multiple categories such as size, colour or brand
    * Average discount percentage or effectiveness by brand.
    
    - Stacked Bar Chart: 
    * Stock quantity by brand,size or color, grouped by size,color or brand.                                       

    - Histogram:
    * Distribution of discount percentages or t shirt prices.
    Note: Total should sum to 100%
                                              
    - Scatter Plots (for numeric relationships):
    * T-shirt price vs. discount percentage to see how discounts vary with price
    * Stock quantity vs. discount percentage to identify trends (e.g., are high-stock items discounted more?).
    * Price vs. stock quantity to see if cheaper t-shirts have higher stock.                                         
    Note: Both axes must be numeric, non-categorical
    
    - Pie chart
    * Proportion of stock contributed by each brand or color.
                                              
    - Box Plot
    * Price range by brand or size to show outliers and spread.
    
    - Bubble Chart
    * Brand (x-axis), size (y-axis), and stock quantity (bubble size), with bubble color representing average discount percentage.
                                              
    Special Cases:
    Raw Data:
    * Individual records → No chart (tabular display)
    * Non-aggregated data → No chart (tabular display)

    Tables in scope:
    - t_shirts: t_shirt_id, brand, color, size, price, stock_quantity
    - discounts: discount_id, t_shirt_id, pct_discount

    Question: {question}
    SQL Query: {query}
    SQL Result: {result}

    Provide your response in the following format:
    Recommended Visualization: [Chart type or "none"]. ONLY use the following names: bar, stacked bar, histogram, pie, scatter, box,bubble plots.
    Reason: [Brief explanation for your recommendation]
    """)
    return viz_prompt
