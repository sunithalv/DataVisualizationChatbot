from langchain import hub
from langchain.prompts import SystemMessagePromptTemplate

def get_prompt_template():
    query_prompt_template = hub.pull("langchain-ai/sql-query-system-prompt")
    current_template=query_prompt_template.messages[0].prompt.template
    # Modifying existing template to add specific instructions for the usecase
    new_template = f"""
    {current_template}

    Additional Instructions:
    - For getting count of t shirts always refer column 'stock_quantity' of 't_shirts' table. If multiple rows are returned calculate sum of column 'stock_quantity' for rows instead of counting the rows returned.
    - For getting the price of t shirts always follow the following steps:
    1. The 'price' column of 't_shirts' table indicates the base price of one t shirt only.
    2. Next,Always check in the 'discounts' table if any entry exists for given t shirt id.
    3. If entry exists 'pct_discount' column in that row refers to the discount percentage for a given t shirt id.
    Calculate discounted price as price*(1-(pct_discount/100)).Else ignore the 'discounts' table.

    """

    # Create a new SystemMessagePromptTemplate with the updated template
    updated_message = SystemMessagePromptTemplate(
        prompt=query_prompt_template.messages[0].prompt.copy(update={"template": new_template})
    )

    # Replace the old message with the updated one
    query_prompt_template.messages[0] = updated_message

    return query_prompt_template