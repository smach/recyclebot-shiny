# This was built using the Shiny Assistant, which is totally awesome. I had it 'translate' an app I first wrote in Chainlit and then had Claude 'translate' into a Streamlit app. 
# Shiny Assistant is at https://gallery.shinyapps.io/assistant/
# There is separate code I wrote myself which processed all the recycling-related documents via LangChain and stored the embeds in Pinecone. 

from shiny import App, reactive, render, ui
from os import environ
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage, HumanMessage
from langchain_community.vectorstores import Pinecone as PineconeLangChain
from pinecone import Pinecone
import html

from dotenv import load_dotenv, find_dotenv
# Load environment variables
_ = load_dotenv(find_dotenv())

# Initialize embeddings and vector store
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

INDEX_NAME = "recycle-info"
pc = Pinecone(api_key=environ.get("PINECONE_API_KEY"))

docsearch = PineconeLangChain.from_existing_index(
    embedding=embeddings,
    index_name=INDEX_NAME,
)


app_ui = ui.page_navbar(
    ui.head_content(
    ui.tags.link(rel="shortcut icon", href="/favicon.ico"),
    ui.tags.meta(name="description", content="Unofficial app answers questions about Framingham's recycling program")
    ),
    ui.nav_panel("💬 Chat",
        ui.card(
            ui.markdown("""
            **Welcome to the Framingham Recycling Assistant!**

            You can ask questions like:
            * 'Can I recycle pizza boxes?'
            * 'Posso reciclar papel picado?'
            * '¿Qué plásticos puedo reciclar?'
            
            You may need to add 'in Framingham', for ex. 'Can I recycle broken glass in Framingham?' The app tries to screen out general queries. This app can understand and answer in multiple languages (although source documents are only in English).
            
            **Note:** This is a demo proof-of-concept only and NOT an official Framingham app! Data come from posts by city Recycling Coordinator Eve Carey and the city website.
            """),
        ),
        ui.card(
            ui.tags.style(
            """
            .form-control {
            border-radius: 10px;
            }
            """
            ),
            ui.input_text("user_message", ui.HTML("<span style='font-size: 1.2em; font-weight: bold;'>Enter your question here:</span>"), width = '50%', placeholder='Your query'),
            ui.input_action_button("send", "Submit query", class_="btn-primary", width = '30%'),
            ui.output_ui("chat_history")
        )
    ),
    ui.nav_panel("❓ FAQ",
        ui.card(
            ui.markdown("""
            # Framingham Recyclebot FAQ

            **Who made this?** This app was created by [Sharon Machlis](https://www.machlis.com) to demo how generative AI 
            might be useful for local governments. It uses technology similar to that behind ChatGPT specifically to answer 
            questions only about the Framingham recycling program, but the idea could apply to a lot of other government 
            services and information. **This is not an official city of Framingham app.**

            **Where does the information come from?** Data come from one page on the city's website and a few posts by 
            Framingham Recycling Coordinator Eve Carey, but the app is not affiliated with the city. You can see official 
            information about the Framingham Recycling program at 
            [Framingham Curbside Recycling](https://www.framinghamma.gov/201/Curbside-Recycling).

            **How does this work?** It first analyzes your question and 'translates' it into a series of numbers called 
            embeddings, and then checks the documents to find excerpts with embeddings that are most similar to your 
            question. Then, your question and those relevant chunks are sent to a Large Language Model to generate an answer.

            **What can I do with this?** You should be able to ask Recyclebot things like

            - Can I recycle pizza boxes in Framingham?
            - What types of plastic can I recycle in Framingham?
            - Can I recycle shredded paper?

            **How does this work?** It first analyzes your question and 'translates' it into a series of numbers called embeddings, and then checks the documents to find excerpts with embeddings that are most similar to your question. Then, your question and those releative chunks are sent to a Large Language Model (same tech as behind ChatGPT) to generate an answer.

            **What specific technologies does it use?** It uses the [Shiny](https://shiny.posit.co/py/) and [LangChain](https://www.langchain.com/) Python frameworks for building custom generative AI applications. [Anthropic's Claude 3 models](https://www.anthropic.com/) are the AI engine generating responses, and an [OpenAI model](https://platform.openai.com/docs/guides/embeddings) - same company behind ChatGPT - retrieves relevant source documents.

            **Sounds interesting! I'm guessing this isn't the only application doing that?** There are a _lot_ efforts underway to create chatbots like this for a lot different use cases, such as software documentation and customer service. We have one at work answering questions about all our articles from Computerworld, CIO, CSO, InfoWorld, and Network World called [Smart Answers](https://www.cio.com/smart-answers/). There's also another, consumer tech version for PCWorld, Macworld, and TechHive at [https://www.pcworld.com/smart-answers](https://www.pcworld.com/smart-answers) if you want to play. These applications are known in the field as RAG (Retrieval Augmented Generation).

            """)
        )
    ),
    title="Framingham Recycling Q&A"
)

def server(input, output, session):
    # Initialize messages as a reactive value
    messages = reactive.value([])
    
    # Initialize LLMs
    checker_llm = ChatAnthropic(
        model_name="claude-3-haiku-20240307",
        temperature=0
    )
    
    # Initialize conversation chain components
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        output_key="answer",
        return_messages=True
    )
    
    chain = ConversationalRetrievalChain.from_llm(
        ChatAnthropic(
            model_name="claude-3-sonnet-20240229",
            temperature=0
        ),
        chain_type="stuff",
        retriever=docsearch.as_retriever(search_kwargs={"k": 3}),
        memory=memory,
        return_source_documents=True
    )
    
    def check_if_recycling_related(question):
        """Check if the question is related to recycling"""
        response = checker_llm.invoke(
            [
                SystemMessage(content="You are a helpful assistant that determines if a given question is related to recycling or not."),
                HumanMessage(content=f"Is the following question related to recycling or what can be recycled? '{question}'")
            ]
        )
        return "no" not in response.content.lower()
    
    def format_source_content(source_docs):
        """Format source documents for display"""
        if not source_docs:
            return ""
        
        source_html = "<div class='sources'><h4>Sources:</h4>"
        for i, doc in enumerate(source_docs):
            source = doc.metadata.get("source", f"Source {i+1}")
            content = html.escape(doc.page_content)
            source_html += f"""
            <details>
                <summary>📄 {source}</summary>
                <div class='source-content'>{content}</div>
            </details>
            """
        source_html += "</div>"
        return source_html
    
    @reactive.effect
    @reactive.event(input.send)
    def process_message():
        msg = input.user_message()
        if msg and msg.strip():
            current_messages = messages.get().copy()
            current_messages.append({"role": "user", "content": msg})
            
            try:
                # Check if question is recycling-related
                if not check_if_recycling_related(msg):
                    response = "Your question does not seem to be related to recycling. This app can only answer questions about the Framingham recycling program."
                    current_messages.append({"role": "assistant", "content": response})
                else:
                    # Get response from chain
                    chain_response = chain(msg)
                    answer = chain_response["answer"]
                    source_docs = chain_response.get("source_documents", [])
                    
                    # Format response with sources
                    response = answer
                    if source_docs:
                        response += format_source_content(source_docs)
                    
                    current_messages.append({"role": "assistant", "content": response})
            
            except Exception as e:
                response = "I apologize, but I'm having trouble generating a response right now. Please try again later."
                current_messages.append({"role": "assistant", "content": response})
            
            messages.set(current_messages)
            ui.update_text("user_message", value="")

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
                    ui.card(
                        ui.HTML(msg["content"]) if not is_user else msg["content"]
                    ),
                    style=(
                        "margin: 10px 0; "
                        f"margin-{'left' if is_user else 'right'}: 20%; "
                        f"background-color: {'#e9ecef' if is_user else '#f8f9fa'};"
                    )
                )
            )
        
        return ui.div(
            ui.tags.style("""
                .sources { margin-top: 15px; border-top: 1px solid #ddd; padding-top: 10px; }
                .source-content { padding: 10px; background: #f8f9fa; margin-top: 5px; }
                details { margin: 5px 0; }
            """),
            message_elements,
            style="max-height: 400px; overflow-y: auto;"
        )

app = App(app_ui, server)