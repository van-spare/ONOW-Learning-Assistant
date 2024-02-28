from openai import OpenAI
import os
import time
from time import sleep
import json
import socket
import asyncio
from IPython.display import display, HTML
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
openAISecret = os.getenv("OPENAI_API_KEY")
# import utils
# from tools import topicList, iscorrect

st.title("ONOW Learning Assistant Beta")

with st.expander("See Instructions"):
    # simple_llm = llmAgent.simple_llm()
    st.info("**Step 1:**\n\n"\
            "Enter your business info\n- Enter your business information to get personalized lessons for your business specific.\n\n"\
            "Which course you do want to learn?\n- Select the course you want to learn.\n\n"\
            "Are you a beginner?\n- Select your level on the course. Depending on your choice, the course topics will change.\n\n"\
            "**Step 2:**\n\n"
            "Create Learning Assistant: Click this to initialize your learning assistant. As assistant is initialized, you will see the topics you will learn.\n\n"\
            "**Step 3:**\n\n"\
            "Start Learning: You can click to let the assistant know that you want to start learning.\n\n"\
            "Take Quiz: Click this to take quizzes.\n\n"
            "**Step 4:** Start the conversation by sending simple 'Hi' or anything.")
# thread, threadid, assistant, assistantid = None, None, None, None
# Initialize client
# topiclist = []
client = OpenAI(
    api_key = openAISecret
)

# from tools import correctness_function, topics_function
import json
# Defining tools
def is_correct(val):
    val = 'true' in val
    global iscorrect
    st.session_state['iscorrect'] = val
    iscorrect=val
    return ""

correctness_function =  {
"type": "function",
"function": {
    "name": "is_correct",
    "description": "Call when determining whether a given answer is correct or incorrect",
    "parameters": {
    "type": "object",
    "properties": {
        "is_correct": {
        "type": "boolean",
        "description": "true if answer is correct, false if not"
        }
    },
    "required": [
        "is_correct"
    ]
    }
}
}

#topic breakdown
# global topicList
# topicList = []
topicList = []
def topics(topics, append=False):
    global topicList
    print("TopicList before:", topicList)
    if(append):
        # global topicList
        topicList.extend(json.loads(topics)['topiclist'])
        # st.session_state['topiclist'].extend(json.loads(topics)['topiclist'])
    else:
        # global topicList
        topicList = json.loads(topics)['topiclist']
        # st.session_state['topiclist'] = json.loads(topics)['topiclist']
    if len(st.session_state['topiclist']) == 0:
        st.session_state['topiclist'] = topicList
    return ""

topics_function =    {
"type": "function",
"function": {
    "name": "topics",
    "description": "Call when creating a list of topics. call only a single time with all topics",
    "parameters": {
    "type": "object",
    "properties": {
        "topiclist": {
        "type": "array",
        "description": "array of topics by name. can take unlimited topics",
        "items": {
            "type": "string"
            }
        }
        },
    "required": [
        "topiclist"
        ]
    }
}
}

def add_files(client, selected_course):
    files = []
    if(selected_course=="Budgeting"):
        file = client.files.create(
        file=open("budgeting.pdf", "rb"),
        purpose='assistants'
        )
        file2 = client.files.create(
        file=open("budgeting2.pdf", "rb"),
        purpose='assistants'
        )
        files.append(file.id)
        files.append(file2.id)

    elif(selected_course=="Saving"):
        file = client.files.create(
        file=open("saving.pdf", "rb"),
        purpose='assistants'
        )
        files.append(file.id)

    elif(selected_course=="Borrowing"):
        file = client.files.create(
        file=open("borrowing.pdf", "rb"),
        purpose='assistants'
        )
        files.append(file.id)

    elif(selected_course=="Export Markets"):
        file = client.files.create(
        file=open("export.pdf", "rb"),
        purpose='assistants'
        )
        files.append(file.id)
    return files

def create_assistant(st, client, info, selected_course, files):
    try:
        assistant = client.beta.assistants.create(
            name="ONOW Assistant Van",
            instructions=f"You are a consultant teaching small business owners about {selected_course}. You only use information contained in your uploaded files. You will not answer any questions about topics unrelated to budgeting or the files unless the question specifically ends with 'off topic allowed', responding only with \"Let's try to stay on topic! Do you have any other questions relating to {selected_course}?\". Don’t justify this response. Don’t give information not mentioned in the CONTEXT INFORMATION. Use simple language that is easy to translate, and avoid jargon. Try to connect examples to my actual business, which is {info}",
            tools=[{"type": "retrieval"},
                correctness_function,
                    topics_function],
            model="gpt-3.5-turbo-1106",
            file_ids = files
        )
        # assistantid = assistant.id
        st.session_state['assistant_created'] = True 
        # st.session_state['topics_created'] = True
        return assistant

    except Exception as e:
        print(e)
    
## Assistant querying function
def query_assistant(client, query, threadid, assistantid):
    message = client.beta.threads.messages.create(
        thread_id=threadid,
        role="user",
        content=query
    )

    #run message
    run = client.beta.threads.runs.create(
          thread_id=threadid,
          assistant_id=assistantid)

    #retrieve message status

    run = client.beta.threads.runs.retrieve(
            thread_id=threadid,
            run_id=run.id
        )

    while True:
        run = client.beta.threads.runs.retrieve(
            thread_id=threadid,
            run_id=run.id
        )

        if run.completed_at != None:
            break

        elif run.required_action != None:
            
            #submit function call response 
            #print(run.required_action.submit_tool_outputs.tool_calls)
            
            outs = []
            seentopics = True
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                fname = globals()[tool_call.function.name]
                if(tool_call.function.name == 'topiclist' and seentopics):
                    outs.append({"tool_call_id": tool_call.id, 
                            "output":fname(tool_call.function.arguments, append=True)})
                elif(tool_call.function.name == 'topiclist'):
                    seentopics = True
                    outs.append({"tool_call_id": tool_call.id, 
                            "output":fname(tool_call.function.arguments)})
                else:
                    outs.append({"tool_call_id": tool_call.id, 
                            "output":fname(tool_call.function.arguments)})

            run = client.beta.threads.runs.submit_tool_outputs(
              thread_id=threadid,
              run_id=run.id,
              tool_outputs=outs
            )
            
    messages = client.beta.threads.messages.list(
      thread_id=threadid
    )
    
    return messages.data[0].content[0].text.value


# initializing sesstion state
if 'create_assistant' not in st.session_state:
    st.session_state['create_assistant'] = False
if 'files_added' not in st.session_state:
    st.session_state['files_added'] = False
if 'assistant_created' not in st.session_state:
    st.session_state['assistant_created'] = False
if 'topics_created' not in st.session_state:
    st.session_state['topics_created'] = False
# Initialize chat history in session state for Document Analysis (doc) if not present
if 'doc_messages' not in st.session_state:
    # Start with first message from assistant
    st.session_state['doc_messages'] = []
if 'assistant_id' not in st.session_state:
    # Start with first message from assistant
    st.session_state['assistant_id'] = None
if 'thread_id' not in st.session_state:
    # Start with first message from assistant
    st.session_state['thread_id'] = None
if 'topiclist' not in st.session_state:
    st.session_state['topiclist'] = []
if 'topic_count' not in st.session_state:
    st.session_state['topic_count'] = 0
if 'topic_quizz_count' not in st.session_state:
    st.session_state['topic_quizz_count'] = 0
if 'selected_course' not in st.session_state:
    st.session_state['selected_course'] = None
if 'learn' not in st.session_state:
    st.session_state['learn'] = False
if 'quiz' not in st.session_state:
    st.session_state['quiz'] = False
if 'score' not in st.session_state:
    st.session_state['score'] = 0
if 'topic_count' not in st.session_state:
    st.session_state['topic_count'] = 0
if 'selected_course' not in st.session_state:
    st.session_state['selected_course'] = None
if 'iscorrect' not in st.session_state:
    st.session_state['iscorrect'] = None

with st.sidebar:
    # User business
    info = st.text_area("Enter your business info:", value="Eg. I am a farmer who grows mostly corn and wheat. I have animals including cows, pigs, and chickens.")

    # Learning topic
    courses = ["Budgeting", "Saving", "Borrowing", "Export Markets"]
    selected_course = st.selectbox("Which course do you want to learn?", courses)
    

    isBeginner = st.radio("Are you a beginner?", ["Yes", "No"])

    if st.button("Create Learning Assistant"):
        st.session_state['create_assistant'] = True
    
    if st.button("Start Learning"):
        st.session_state['learn'] = True
        st.session_state['quiz'] = False
        if st.session_state['assistant_created']:
            assistant_response = "You can start learning. Type 'continue' or 'start' to continue."
            st.session_state['doc_messages'].append({"role": "assistant", "content": assistant_response})
            # with st.chat_message("assistant"):
            #     st.markdown(assistant_response)
    
    if st.button("Take Quiz"):
        st.session_state['quiz'] = True
        st.session_state['learn'] = False
        if st.session_state['assistant_created']:
            assistant_response = "You can start quizz. Type 'continue' or 'start' to continue."
            st.session_state['doc_messages'].append({"role": "assistant", "content": assistant_response})
            # with st.chat_message("assistant"):
            #     st.markdown(assistant_response)

# Function to update session_state
if selected_course != st.session_state.selected_course:
    st.session_state.conversation = None
    st.session_state['selected_course'] = selected_course
    st.session_state['create_assistant'] = False
    st.session_state['files_added'] = False
    st.session_state['assistant_created'] = False
    st.session_state['topics_created'] = False
    st.session_state['doc_messages'] = []
    st.session_state['assistant_id'] = None
    st.session_state['thread_id'] = None
    st.session_state['topiclist'] = []
    st.session_state['quiz'] = False
    st.session_state['learn'] = False
    st.session_state['topic_count'] = 0
    st.session_state['topic_quizz_count'] = 0
    st.session_state['score'] = 0
    st.session_state['iscorrect'] = None

# Initialing assistant
#create thread
thread = client.beta.threads.create()
# threadid = thread.id
st.session_state['thread_id'] = thread.id

files = []
# assistantid = None
# Adding files to client
if st.session_state['create_assistant'] and not st.session_state['assistant_created']:
    with st.spinner("Creating your learning assistant for course selected..."):

        files = add_files(client, selected_course)
        assistant = create_assistant(st=st,client=client,info=info,selected_course=selected_course,files=files)
        assistantid = assistant.id
        st.session_state['assistant_id'] = assistantid
        

    with st.spinner("Creating topics for the selected course ..."):
        initial_question = f"Break all of your file material down into a set of 15 topics that I can use to learn about {selected_course}. Make these small, specific topics. Assume I know nothing about {selected_course} yet. Provide just the topics in a list, without any additional messages before or after. Ex. for 'Budgeting': 1. learning how to budget. 2. budgeting strategies 3. Calculating monthly income"

        #this query will trigger an openai assistants function call that sets the global variable "topicList". I enabled this in the tooo
        assistant_response = query_assistant(client=client,query=initial_question, threadid=st.session_state['thread_id'], assistantid=st.session_state['assistant_id'])
        # topiclist = assistant_response
        # print("Tpics divided:",topiclist)
        st.session_state['doc_messages'].append({"role": "assistant", "content": assistant_response})
# assistantid = st.session_state['assistant_id']
# st.info(f'Assistant successfully created with id: {assistantid}')
st.write(f"You've chosen the topic: **{selected_course}**. Welcome to your course!")
# Display previous chat messages
for message in st.session_state['doc_messages']:
    with st.chat_message(message['role']):
        st.write(message['content'])

topiclist = st.session_state['topiclist']
# topiclist = topicList
if user_query := st.chat_input("Enter your query here"):
    # global topicList
    # print()
    print('\nTopic list for course:', topiclist)
    # Append user message
    
    st.session_state['doc_messages'].append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # Attempt to start learning topics one by one
    if st.session_state['learn']:
        print("You are learning...")
        print("Topic count:", st.session_state['topic_count'])
        if user_query.lower() in ['hi','start','continue']:
            print("You go to next topic ...")
            
            if st.session_state['topic_count'] >= len(topiclist):
                print("You have learned all ...")
                # print("HERE 1")
                assistant_response = f"You have learned all the topics about {selected_course}"
                st.session_state['doc_messages'].append({"role": "assistant", "content": assistant_response})
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)
            else:
                print("Next topic ... ")
                print("Topic name:", topiclist[st.session_state['topic_count']])
                query = "Teach me about " + topiclist[st.session_state['topic_count']] + " in simple words, connecting it to my business. (off topic allowed)"
                with st.spinner('Generating response...'):
                    assistant_response = f"\nTopic {st.session_state['topic_count'] + 1}: {topiclist[st.session_state['topic_count']]}\n\n" + query_assistant(client=client,query=query, threadid=st.session_state['thread_id'], assistantid=st.session_state['assistant_id'])
                    st.session_state['doc_messages'].append({"role": "assistant", "content": assistant_response})
                    with st.chat_message("assistant"):
                        st.markdown(assistant_response)
                st.session_state['topic_count'] += 1
                
                assistant_response = "\nDo you have any questions about this topic? Otherwise, please type \"continue\"."
                st.session_state['doc_messages'].append({"role": "assistant", "content": assistant_response})
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)

        # staying at the current topic
        elif user_query.lower() != "continue":
            print("HERE 3")
            with st.spinner('Generating response...'):
                assistant_response = "\n" + query_assistant(client=client,query=user_query, threadid=st.session_state['thread_id'], assistantid=st.session_state['assistant_id'])
                st.session_state['doc_messages'].append({"role": "assistant", "content": assistant_response})
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)

            # response = input("\n" + "If this answered your question, type \"continue\", otherwise keep asking questions! >>> ")
            assistant_response = "If this answered your question, type \"continue\", otherwise keep asking questions! >>> "
            st.session_state['doc_messages'].append({"role": "assistant", "content": assistant_response})
            with st.chat_message("assistant"):
                st.markdown(assistant_response)
    elif st.session_state['quiz']:
        print("Quizz")
        print("Quizz count:", st.session_state['topic_quizz_count'])
        print("Quizz topic:", topiclist[st.session_state['topic_quizz_count']])

        ## checking user answer
        if user_query.lower() in ['a','b','c','d']:

            print("You are answering the previous question...")
            query = f"Is {user_query} the correct answer? If not, tell me what the correct answer is and explain why."
            with st.spinner('Generating response...'):
                assistant_response = query_assistant(client=client,query=query,threadid=st.session_state['thread_id'],assistantid=st.session_state['assistant_id'])
                st.session_state['doc_messages'].append({"role": "assistant", "content": assistant_response})
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)
                st.session_state['topic_quizz_count'] += 1

            if(st.session_state['iscorrect']):
                st.session_state['score'] +=1

        ## end of topic
        if st.session_state['topic_quizz_count'] >= len(topiclist):
            print("You finished the quizz.")
            assistant_response = f"You've finished the course with a score of {st.session_state['score']}! Congratulations, you are now proficient in {selected_course}!"
            st.session_state['doc_messages'].append({"role": "assistant", "content": assistant_response})
            with st.chat_message("assistant"):
                st.markdown(assistant_response)
        else:
            ## generating next quizz
            print("Not finished yet, next quizz")
            print("Quizz topic:", topiclist[st.session_state['topic_quizz_count']])
            query = f"Give me a multiple choice quiz question about {topiclist[st.session_state['topic_quizz_count']]} from the files uploaded. DO NOT include anything besides the question, and 4 answer choices, labeled A-D each separated by two lines. Do not tell me the answer."
            with st.spinner('Generating next quiz...'):
                assistant_response = f"Quiz for topic: {st.session_state['topic_quizz_count'] + 1} {topiclist[st.session_state['topic_quizz_count']]} \n\n"
                query_ = query_assistant(client=client,query=query,threadid=st.session_state['thread_id'],assistantid=st.session_state['assistant_id'])
                assistant_response = assistant_response + query_ + "\n\nWhich is the correct answer: A, B, C, or D?"
                st.session_state['doc_messages'].append({"role": "assistant", "content": assistant_response})
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)
        
