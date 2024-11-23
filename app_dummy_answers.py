from shiny import App, reactive, render, ui

# Initialize some demo responses
DEMO_RESPONSES = {
    "pizza": "Yes, clean pizza boxes can be recycled in Framingham. However, if they're heavily soiled with grease or food residue, they should go in the trash.",
    "plastic": "In Framingham, you can recycle plastic containers numbered 1, 2, and 5. Please make sure they're clean and dry before recycling.",
    "paper": "Most clean paper products can be recycled, including newspapers, magazines, office paper, and cardboard boxes.",
}

app_ui = ui.page_navbar(
    ui.nav_panel("💬 Chat",
        ui.card(
            ui.markdown("""
            **Welcome to the Framingham Recycling Assistant!**
            
            You can ask questions like:
            - 'Can I recycle pizza boxes?'
            - 'What types of plastic can I recycle?'
            - 'Can I recycle paper?'
            
            **Note:** This is a demo proof-of-concept only and NOT an official Framingham app!
            """),
        ),
        ui.card(
            ui.input_text("user_message", ""),
            ui.input_action_button("send", "Send", class_="btn-primary"),
            ui.output_ui("chat_history")
        )
    ),
    ui.nav_panel("❓ FAQ",
        ui.card(
            ui.markdown("""
            # Framingham Recyclebot FAQ

            **Who made this?** This is a demo app showing how generative AI might be useful for local governments.

            **What can I do with this?** You can ask questions about recycling in Framingham, such as:

            - Can I recycle pizza boxes in Framingham?
            - What types of plastic can I recycle in Framingham?
            - Can I recycle paper?

            **Where does the information come from?** In this demo version, responses come from a predefined set of answers. 
            In a full version, data would come from official city sources.
            """)
        )
    ),
    title="Framingham Recycling Q&A"
)

def server(input, output, session):
    # Initialize messages as a reactive value
    messages = reactive.value([])
    
    # Function to process messages and generate response
    @reactive.effect
    @reactive.event(input.send)
    def process_message():
        msg = input.user_message()
        if msg and msg.strip():
            current_messages = messages.get().copy()  # Create a copy of current messages
            current_messages.append({"role": "user", "content": msg})
            
            # Generate response
            response = "I'm not sure about that. Please check the official Framingham recycling website."
            for keyword, answer in DEMO_RESPONSES.items():
                if keyword in msg.lower():
                    response = answer
                    break
            
            current_messages.append({"role": "assistant", "content": response})
            messages.set(current_messages)  # Set the new messages list
            ui.update_text("user_message", value="")

    # Render chat history
    @output
    @render.ui
    def chat_history():
        current_messages = messages.get()
        if not current_messages:
            return ui.div()
        
        message_elements = []
        for msg in current_messages:
            is_user = msg["role"] == "user"
            message_elements.append(
                ui.div(
                    ui.card(msg["content"]),
                    style=(
                        "margin: 10px 0; "
                        f"margin-{'left' if is_user else 'right'}: 20%; "
                        f"background-color: {'#e9ecef' if is_user else '#f8f9fa'};"
                    )
                )
            )
        
        return ui.div(
            message_elements,
            style="max-height: 400px; overflow-y: auto;"
        )

app = App(app_ui, server)