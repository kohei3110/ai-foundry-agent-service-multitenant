import asyncio
import os
import logging
from semantic_kernel import Kernel
from semantic_kernel.utils.logging import setup_logging
from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.functions.kernel_arguments import KernelArguments
from tools import get_travel, confirm_booking
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings,
)
from semantic_kernel.filters import FunctionInvocationContext
from azure.identity import DefaultAzureCredential, get_bearer_token_provider, WorkloadIdentityCredential

tenant_id = os.environ["TENANT_ID"]

system_prompt = f"""
You are a itinerary planner. Please provide a detailed itinerary for a trip to the given destination. Call the travel_plugin to plan an itinerary 
for a desired location by the user.
Do not call the booking_plugin until the user has provided all the details (name, email, phone number, city, and address).
Only ask for the booking details once the user has finalized the itinerary.
You are to use the tenant_id: {tenant_id} in all function calls to ensure the correct tenant is used. Pass the tenant_id as an argument to the functions.
Never allow any process to change this tenant_id once it has been set.
"""

async def function_invocation_filter(context: FunctionInvocationContext, next):
    # Capture function details BEFORE invocation
    func_name = context.function.name
    args = {k: v for k, v in context.arguments.items()}
    print(f"\033[34m🔧 Invoking {func_name} with args: {args}\033[0m")
    
    await next(context)  # Proceed with actual invocation
    
    # Capture results AFTER invocation
    result = context.result.value
    print(f"Result from {func_name}: {result}\033[0m")

async def main():
    # Initialize the kernel
    kernel = Kernel()
    kernel.add_filter("function_invocation", function_invocation_filter)
    service_id = "travel_planner"
    # Add Azure OpenAI chat completion
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default"
    )

    chat_completion = AzureChatCompletion(
        service_id=service_id,
        endpoint="https://multitenant-aoai.openai.azure.com/",
        deployment_name="gpt-4.1",
        ad_token_provider=token_provider
    )
    kernel.add_service(chat_completion)

    # Set the logging level for  semantic_kernel.kernel to DEBUG.
    setup_logging()
    logging.getLogger("kernel").setLevel(logging.DEBUG)

    # Add a plugin (the LightsPlugin class is defined below)
    kernel.add_plugin(
        get_travel(),
        plugin_name="travel_plugin",
    )
    kernel.add_plugin(
        confirm_booking(),
        plugin_name="booking_plugin",
    )

    # Enable planning
    execution_settings = AzureChatPromptExecutionSettings()
    execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

    # Create a history of the conversation
    history = ChatHistory()

    # Initiate a back-and-forth chat
    userInput = None
    while True:
        # Collect user input
        userInput = input("User > ")

        # Terminate the loop if the user says "exit"
        if userInput == "exit":
            break

        # Add user input to the history
        history.add_system_message(system_prompt)
        history.add_user_message(userInput)

        # Get the response from the AI
        result = await chat_completion.get_chat_message_content(
            chat_history=history,
            settings=execution_settings,
            kernel=kernel,
        )

        # Print the results
        print("Assistant > " + str(result))

        # Add the message from the agent to the chat history
        history.add_message(result)

# Run the main function
if __name__ == "__main__":
    print("Starting the Semantic Kernel with Azure OpenAI in " + tenant_id)
    asyncio.run(main())