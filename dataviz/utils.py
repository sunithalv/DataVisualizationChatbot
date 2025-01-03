import streamlit as st
import plotly.express as px
import plotly.colors as pcolors  
import altair as alt
import pandas as pd
import json
import io

def display_visualization(response,chart_type):
    #get the chart_data from state as dictionary
    try:
        print("Response in display_visualization:", response)
        content = response.replace(
            '```json', '').replace('```', '').strip()
        parsed_data = json.loads(content)
        print("Parsed data in display_visualization:", parsed_data)
        print("Chart data in display_visualization:", parsed_data.get("chart_data"))
        print("Chart type in display_visualization:", chart_type)
        if chart_data := parsed_data.get("chart_data"):
        
            if chart_type == "bar":
                df = pd.DataFrame({
                    'Category': chart_data['labels'],
                    'Value': chart_data['values'][0]['data']
                })
                # Dynamically generate a color palette based on the number of categories
                num_categories = len(df['Category'])
                color_palette = pcolors.qualitative.Plotly[:num_categories]
                # Get the label
                x_label=chart_data.get('x_label')
                y_label=chart_data['values'][0]['label']
                chart_label = "Bar Chart for " + chart_data.get('title')

                # Create the bar chart using Plotly
                chart = px.bar(
                    df,
                    x="Category",
                    y="Value",
                    title=chart_label,
                    color="Category",  # Assign colors to categories
                    color_discrete_sequence=color_palette
                )

                # Customize tooltips and layout
                chart.update_traces(
                    hovertemplate="<b>%{x}</b><br>Value: %{y}<extra></extra>"
                )

                chart.update_layout(
                    xaxis_title=x_label,
                    yaxis_title=y_label,
                    #title_x=0.5,  # Center the title
                    title_font=dict(size=18, weight='bold'),
                )

            elif chart_type == "stacked bar":
                # Prepare the DataFrame
                data = []
                for group in chart_data["stack_groups"]:
                    for i, count in enumerate(group["counts"]):
                        data.append({
                            "Size": chart_data["x_axis_categories"][i],
                            "Count": count,
                            "Color": group["stack_category"]
                        })

                df = pd.DataFrame(data)
                # Dynamically generate a color palette based on the number of stack categories
                stack_categories = [group["stack_category"] for group in chart_data["stack_groups"]]
                color_palette = pcolors.qualitative.Plotly[:len(stack_categories)]
                chart_label = "Stacked Bar Chart for " + chart_data.get('title')
                # Create the stacked bar chart using Plotly
                chart = px.bar(
                    df,
                    x="Size",
                    y="Count",
                    color="Color",
                    title=chart_label,
                    labels={"Size": chart_data.get("x_label", "X-Axis"), "Count": chart_data.get("y_label", "Y-Axis")},
                    color_discrete_sequence=color_palette,  # Apply the dynamic color palette
                )

                # Customize the layout
                chart.update_layout(
                    barmode="stack",  # Enable stacking
                    #title_x=0.5,  # Center the title
                    title_font=dict(size=18, weight="bold"),
                    xaxis_title=chart_data.get("x_label", "X-Axis"),
                    yaxis_title=chart_data.get("y_label", "Y-Axis"),
                )
            
            elif chart_type == "pie":
                # Prepare data for the pie chart
                df = pd.DataFrame({
                    'Category': [item['label'] for item in chart_data['data']],
                    'Value': [item['value'] for item in chart_data['data']]
                })
                # Dynamically generate a color palette based on the number of categories
                num_categories = len(df['Category'])
                color_palette = pcolors.qualitative.Plotly[:num_categories]
                chart_label = "Pie Chart for " + chart_data.get('title')

                # Create the donut chart using Plotly
                chart = px.pie(
                    df,
                    values="Value",
                    names="Category",
                    title=chart_label,
                    hole=0.4,  # Creates the donut effect
                )

                # Customize tooltips to include percentages
                chart.update_traces(
                    textinfo="percent+label",  # Show both percentage and label
                    hovertemplate="<b>%{label}</b><br>Value: %{value}<br>Percentage: %{percent}<extra></extra>",
                    marker=dict(colors=color_palette)
                )
            elif chart_type == "histogram":
                # Prepare the DataFrame
                df = pd.DataFrame({
                    "Bins": chart_data["bins"],
                    "Counts": chart_data["counts"]
                })
                chart_label="Histogram for " + chart_data.get('title')
                # Create the histogram using Plotly
                chart=px.histogram(
                    df, x="Bins", y="Counts",
                    title=chart_label, 
                    labels={"Bins": chart_data.get("x_label", "X-Axis"), 
                            "Counts": chart_data.get("y_label", "Y-Axis")},
                    histfunc='sum',  # Use the provided counts
                    color_discrete_sequence=["#ADD8E6"]  # Set color to light blue
                    )
                
                # Update layout for the histogram
                chart.update_layout(
                    #title_x=0.5,  # Center the title
                    title_font=dict(size=18, weight="bold"),
                    xaxis=dict(
                        tickmode="array",
                        tickvals=df["Bins"],  # Show bin values as ticks
                    ),
                )
            elif chart_type == "scatter":
                # Convert data points to DataFrame
                df = pd.DataFrame(chart_data["data_points"])
                chart_label="Scatter plot for " + chart_data.get('title')
                chart=px.scatter(df, x="x", y="y", 
                 labels={"x": chart_data["x_label"], "y": chart_data["y_label"]},
                 title=chart_label,hover_data={"x": True, "y": True},
                 color_discrete_sequence=["#636EFA"]  # Set color to blue
                 )

            # Render the chart in Streamlit
            st.plotly_chart(chart, use_container_width=True)

    except Exception as e:
        #print('Not able to display chart:', str(e))
        st.warning(f"Could not display chart: {str(e)}")
    
    return chart,chart_label

def download_chart_as_html(chart):
    # Generate the HTML content for the chart
    html_data = chart.to_html(full_html=True, include_plotlyjs='cdn')
    return html_data
