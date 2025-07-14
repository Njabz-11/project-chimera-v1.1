"""
Project Chimera - God-View Dashboard
Real-time monitoring and control interface for the Autonomous Business Operations Platform

This Streamlit dashboard provides:
- Real-time log streaming via WebSocket
- System status monitoring
- Mission management interface
- Agent activity visualization
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import queue

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import websocket
import rel

# Page configuration
st.set_page_config(
    page_title="Project Chimera - God-View Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Global variables for WebSocket and data storage
log_queue = queue.Queue()
system_data = {
    "logs": [],
    "status": {},
    "missions": [],
    "leads": [],
    "agents": {}
}

class ChimeraDashboard:
    def __init__(self):
        self.api_base = "http://localhost:8000"
        self.ws_url = "ws://localhost:8000/ws/logs"
        self.email_polling_status = False
        self.ws = None
        self.connected = False
        
    def connect_websocket(self):
        """Connect to WebSocket for real-time logs"""
        try:
            def on_message(ws, message):
                try:
                    log_data = json.loads(message)
                    log_queue.put(log_data)
                except Exception as e:
                    st.error(f"Error parsing log message: {e}")
            
            def on_error(ws, error):
                st.error(f"WebSocket error: {error}")
                self.connected = False
            
            def on_close(ws, close_status_code, close_msg):
                st.warning("WebSocket connection closed")
                self.connected = False
            
            def on_open(ws):
                self.connected = True
                st.success("Connected to Project Chimera!")
            
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            # Run WebSocket in a separate thread
            def run_ws():
                self.ws.run_forever(dispatcher=rel, reconnect=5)
                rel.signal(2, rel.abort)
                rel.dispatch()
            
            ws_thread = threading.Thread(target=run_ws, daemon=True)
            ws_thread.start()
            
        except Exception as e:
            st.error(f"Failed to connect to WebSocket: {e}")
    
    def fetch_system_status(self):
        """Fetch system status from API"""
        try:
            response = requests.get(f"{self.api_base}/status", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            st.error(f"Failed to fetch system status: {e}")
        return {}
    
    def fetch_missions(self):
        """Fetch missions from API"""
        try:
            response = requests.get(f"{self.api_base}/missions", timeout=5)
            if response.status_code == 200:
                return response.json().get("missions", [])
        except Exception as e:
            st.error(f"Failed to fetch missions: {e}")
        return []
    
    def fetch_leads(self):
        """Fetch leads from API"""
        try:
            response = requests.get(f"{self.api_base}/leads", timeout=5)
            if response.status_code == 200:
                return response.json().get("leads", [])
        except Exception as e:
            st.error(f"Failed to fetch leads: {e}")
        return []
    
    def create_mission(self, briefing_data):
        """Create a new mission"""
        try:
            response = requests.post(f"{self.api_base}/mission/create", json=briefing_data, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            st.error(f"Failed to create mission: {e}")
        return None

    def trigger_lead_search(self, search_data):
        """Trigger a lead search via the Prospector agent"""
        try:
            response = requests.post(f"{self.api_base}/agent/prospector/search", json=search_data, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            st.error(f"Failed to trigger lead search: {e}")
        return None

    # Phase 3: Email and Conversation Management Methods
    def fetch_conversations(self):
        """Fetch conversations from API"""
        try:
            response = requests.get(f"{self.api_base}/conversations", timeout=5)
            if response.status_code == 200:
                return response.json().get("conversations", [])
        except Exception as e:
            st.error(f"Failed to fetch conversations: {e}")
        return []

    def fetch_detailed_status(self):
        """Fetch detailed system status including email metrics"""
        try:
            response = requests.get(f"{self.api_base}/system/status/detailed", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            st.error(f"Failed to fetch detailed status: {e}")
        return {}

    def start_email_polling(self, interval_minutes=5):
        """Start email polling"""
        try:
            response = requests.post(f"{self.api_base}/email/start_polling",
                                   params={"interval_minutes": interval_minutes}, timeout=10)
            if response.status_code == 200:
                self.email_polling_status = True
                return True
        except Exception as e:
            st.error(f"Failed to start email polling: {e}")
        return False

    def stop_email_polling(self):
        """Stop email polling"""
        try:
            response = requests.post(f"{self.api_base}/email/stop_polling", timeout=10)
            if response.status_code == 200:
                self.email_polling_status = False
                return True
        except Exception as e:
            st.error(f"Failed to stop email polling: {e}")
        return False

    def trigger_outreach(self):
        """Trigger outreach for new leads"""
        try:
            response = requests.post(f"{self.api_base}/outreach/trigger", timeout=10)
            return response.status_code == 200
        except Exception as e:
            st.error(f"Failed to trigger outreach: {e}")
        return False

def main():
    # Initialize dashboard
    if 'dashboard' not in st.session_state:
        st.session_state.dashboard = ChimeraDashboard()
        st.session_state.dashboard.connect_websocket()
    
    dashboard = st.session_state.dashboard
    
    # Header
    st.title("🤖 Project Chimera - God-View Dashboard")
    st.markdown("**Autonomous Business Operations Platform (ABOP)**")
    
    # Connection status
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if dashboard.connected:
            st.success("🟢 Connected to Chimera Core")
        else:
            st.error("🔴 Disconnected from Chimera Core")
            if st.button("Reconnect"):
                dashboard.connect_websocket()
    
    with col2:
        if st.button("🔄 Refresh Data"):
            st.rerun()
    
    with col3:
        auto_refresh = st.checkbox("Auto-refresh (5s)", value=True)
    
    # Process incoming logs
    while not log_queue.empty():
        try:
            log_data = log_queue.get_nowait()
            system_data["logs"].append(log_data)
            # Keep only last 1000 logs
            if len(system_data["logs"]) > 1000:
                system_data["logs"] = system_data["logs"][-1000:]
        except queue.Empty:
            break
    
    # Fetch latest data
    system_data["status"] = dashboard.fetch_system_status()
    system_data["missions"] = dashboard.fetch_missions()
    system_data["leads"] = dashboard.fetch_leads()
    
    # Sidebar - System Status
    with st.sidebar:
        st.header("📊 System Status")
        
        status = system_data["status"]
        if status:
            st.metric("Status", status.get("status", "unknown").upper())
            st.metric("Active Agents", status.get("active_agents", 0))
            st.metric("Total Leads", status.get("total_leads", 0))
            st.metric("Active Missions", status.get("active_missions", 0))
            st.metric("Uptime", status.get("uptime", "unknown"))
        else:
            st.warning("No status data available")
        
        st.header("🎯 Quick Actions")
        if st.button("🚨 Emergency Stop"):
            st.error("Emergency stop activated!")
        
        if st.button("📈 Generate Report"):
            st.info("Report generation initiated...")
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["📡 Live Logs", "🎯 Missions", "👥 Leads", "📧 Conversations", "📝 Content", "📦 Fulfillment", "🤖 Agents", "🔧 Technician"])
    
    with tab1:
        st.header("📡 Real-time System Logs")
        
        # Log filters
        col1, col2, col3 = st.columns(3)
        with col1:
            level_filter = st.selectbox("Log Level", ["ALL", "INFO", "WARNING", "ERROR", "DEBUG"])
        with col2:
            agent_filter = st.selectbox("Agent", ["ALL"] + list(set([log.get("agent", "") for log in system_data["logs"]])))
        with col3:
            max_logs = st.number_input("Max Logs", min_value=10, max_value=1000, value=100)
        
        # Filter logs
        filtered_logs = system_data["logs"]
        if level_filter != "ALL":
            filtered_logs = [log for log in filtered_logs if log.get("level") == level_filter]
        if agent_filter != "ALL":
            filtered_logs = [log for log in filtered_logs if log.get("agent") == agent_filter]
        
        # Display logs
        filtered_logs = filtered_logs[-max_logs:]
        
        if filtered_logs:
            for log in reversed(filtered_logs):
                timestamp = log.get("timestamp", "")
                level = log.get("level", "INFO")
                agent = log.get("agent", "UNKNOWN")
                message = log.get("message", "")
                
                # Color code by level
                if level == "ERROR":
                    st.error(f"**{timestamp}** | **{agent}** | {message}")
                elif level == "WARNING":
                    st.warning(f"**{timestamp}** | **{agent}** | {message}")
                elif level == "INFO":
                    st.info(f"**{timestamp}** | **{agent}** | {message}")
                else:
                    st.text(f"{timestamp} | {agent} | {message}")
        else:
            st.info("No logs available. Waiting for system activity...")
    
    with tab2:
        st.header("🎯 Mission Control")
        
        # Mission creation form
        with st.expander("➕ Create New Mission"):
            with st.form("mission_form"):
                business_goal = st.text_area("Business Goal", placeholder="Describe your business objective...")
                target_audience = st.text_input("Target Audience", placeholder="Who are your ideal customers?")
                brand_voice = st.selectbox("Brand Voice", ["Professional", "Friendly", "Authoritative", "Casual", "Technical"])
                
                services = st.text_area("Service Offerings", placeholder="List your services (one per line)")
                
                col1, col2 = st.columns(2)
                with col1:
                    contact_email = st.text_input("Contact Email")
                with col2:
                    contact_phone = st.text_input("Contact Phone")
                
                submitted = st.form_submit_button("🚀 Launch Mission")
                
                if submitted and business_goal and target_audience:
                    briefing_data = {
                        "business_goal": business_goal,
                        "target_audience": target_audience,
                        "brand_voice": brand_voice,
                        "service_offerings": services.split('\n') if services else [],
                        "contact_info": {
                            "email": contact_email,
                            "phone": contact_phone
                        }
                    }
                    
                    result = dashboard.create_mission(briefing_data)
                    if result:
                        st.success(f"Mission created successfully! ID: {result.get('mission_id')}")
                    else:
                        st.error("Failed to create mission")
        
        # Display existing missions
        st.subheader("📋 Active Missions")
        if system_data["missions"]:
            for mission in system_data["missions"]:
                with st.expander(f"Mission: {mission.get('business_goal', 'Unknown')[:50]}..."):
                    st.json(mission)
        else:
            st.info("No active missions. Create one above to get started!")
    
    with tab3:
        st.header("👥 Lead Management")

        # Lead Search Interface
        with st.expander("🔍 Find New Leads", expanded=True):
            with st.form("lead_search_form"):
                col1, col2 = st.columns([3, 1])

                with col1:
                    search_query = st.text_input(
                        "Search Query",
                        placeholder="e.g., 'plumbers in New York', 'digital marketing agencies', 'restaurants in Chicago'"
                    )

                with col2:
                    mission_select = st.selectbox(
                        "Mission",
                        options=[(m.get("id"), m.get("business_goal", "Unknown")[:30] + "...")
                                for m in system_data["missions"]] if system_data["missions"] else [(None, "No missions available")],
                        format_func=lambda x: x[1] if x else "Select Mission"
                    )

                # Search options
                col1, col2 = st.columns(2)
                with col1:
                    search_sources = st.multiselect(
                        "Search Sources",
                        options=["google_maps", "google_search"],
                        default=["google_maps", "google_search"]
                    )

                with col2:
                    max_leads = st.number_input("Max Leads", min_value=5, max_value=100, value=25)

                search_submitted = st.form_submit_button("🚀 Start Lead Search", type="primary")

                if search_submitted and search_query and mission_select[0]:
                    # Trigger lead search via API
                    search_data = {
                        "search_query": search_query,
                        "mission_id": mission_select[0],
                        "sources": search_sources,
                        "max_leads": max_leads
                    }

                    result = dashboard.trigger_lead_search(search_data)
                    if result:
                        st.success(f"Lead search initiated! Job ID: {result.get('job_id')}")
                        st.info("Check the Live Logs tab to monitor progress.")
                    else:
                        st.error("Failed to start lead search")
                elif search_submitted:
                    if not search_query:
                        st.error("Please enter a search query")
                    if not mission_select[0]:
                        st.error("Please select a mission")

        # Display existing leads
        st.subheader("📋 Current Leads")
        if system_data["leads"]:
            # Convert to DataFrame for better display
            df_leads = pd.DataFrame(system_data["leads"])

            # Lead filters
            col1, col2, col3 = st.columns(3)
            with col1:
                status_filter = st.selectbox("Filter by Status", ["All"] + list(df_leads["status"].unique()) if "status" in df_leads.columns else ["All"])
            with col2:
                source_filter = st.selectbox("Filter by Source", ["All"] + list(df_leads["lead_source"].unique()) if "lead_source" in df_leads.columns else ["All"])
            with col3:
                sort_by = st.selectbox("Sort by", ["created_at", "company_name", "qualification_score"])

            # Apply filters
            filtered_df = df_leads.copy()
            if status_filter != "All" and "status" in df_leads.columns:
                filtered_df = filtered_df[filtered_df["status"] == status_filter]
            if source_filter != "All" and "lead_source" in df_leads.columns:
                filtered_df = filtered_df[filtered_df["lead_source"] == source_filter]

            # Sort
            if sort_by in filtered_df.columns:
                filtered_df = filtered_df.sort_values(sort_by, ascending=False)

            st.dataframe(filtered_df, use_container_width=True)

            # Lead statistics
            if not df_leads.empty:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Leads", len(df_leads))
                with col2:
                    qualified_leads = len(df_leads[df_leads.get("status", "") == "qualified"]) if "status" in df_leads.columns else 0
                    st.metric("Qualified Leads", qualified_leads)
                with col3:
                    new_leads = len(df_leads[df_leads.get("status", "") == "new"]) if "status" in df_leads.columns else 0
                    st.metric("New Leads", new_leads)
                with col4:
                    conversion_rate = (qualified_leads / len(df_leads) * 100) if len(df_leads) > 0 else 0
                    st.metric("Conversion Rate", f"{conversion_rate:.1f}%")
        else:
            st.info("No leads found. Use the search form above to find new leads!")

    with tab4:
        st.header("📧 Email & Conversation Management")

        # Email polling controls
        st.subheader("📬 Email Polling")
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            detailed_status = dashboard.fetch_detailed_status()
            email_status = detailed_status.get("email_polling_active", False)
            if email_status:
                st.success("🟢 Email polling is ACTIVE")
                last_check = detailed_status.get("last_email_check")
                if last_check:
                    st.info(f"Last check: {last_check}")
            else:
                st.warning("🟡 Email polling is INACTIVE")

        with col2:
            if st.button("▶️ Start Polling"):
                if dashboard.start_email_polling():
                    st.success("Email polling started!")
                    st.rerun()

        with col3:
            if st.button("⏹️ Stop Polling"):
                if dashboard.stop_email_polling():
                    st.success("Email polling stopped!")
                    st.rerun()

        # Outreach controls
        st.subheader("📤 Outreach Management")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🚀 Trigger Outreach for New Leads"):
                if dashboard.trigger_outreach():
                    st.success("Outreach triggered for all new leads!")
                else:
                    st.error("Failed to trigger outreach")

        with col2:
            # Lead selection for individual outreach
            leads_data = system_data.get("leads", [])
            if leads_data:
                lead_options = {f"{lead.get('company_name', 'Unknown')} (ID: {lead.get('id')})": lead.get('id')
                              for lead in leads_data if lead.get('status') == 'new'}

                if lead_options:
                    selected_lead = st.selectbox("Select lead for outreach:", list(lead_options.keys()))
                    if st.button("📧 Draft Outreach Email"):
                        lead_id = lead_options[selected_lead]
                        if dashboard.draft_outreach_for_lead(lead_id):
                            st.success(f"Outreach email drafted for {selected_lead}")
                        else:
                            st.error("Failed to draft outreach email")

        # Conversations display
        st.subheader("💬 Recent Conversations")
        conversations = dashboard.fetch_conversations()

        if conversations:
            # Create DataFrame for conversations
            df_conversations = pd.DataFrame(conversations)

            # Display conversation metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_conversations = len(df_conversations)
                st.metric("Total Conversations", total_conversations)
            with col2:
                incoming_count = len(df_conversations[df_conversations.get("message_type", "") == "incoming"])
                st.metric("Incoming Messages", incoming_count)
            with col3:
                outgoing_count = len(df_conversations[df_conversations.get("message_type", "") == "outgoing"])
                st.metric("Outgoing Messages", outgoing_count)
            with col4:
                unread_count = len(df_conversations[df_conversations.get("status", "") == "unread"])
                st.metric("Unread Messages", unread_count)

            # Filter conversations
            col1, col2 = st.columns(2)
            with col1:
                message_type_filter = st.selectbox("Message Type", ["All", "incoming", "outgoing"])
            with col2:
                status_filter = st.selectbox("Status", ["All", "unread", "read", "replied", "draft"])

            # Apply filters
            filtered_conversations = df_conversations.copy()
            if message_type_filter != "All":
                filtered_conversations = filtered_conversations[filtered_conversations.get("message_type", "") == message_type_filter]
            if status_filter != "All":
                filtered_conversations = filtered_conversations[filtered_conversations.get("status", "") == status_filter]

            # Display conversations table
            if not filtered_conversations.empty:
                # Select relevant columns for display
                display_columns = ["created_at", "company_name", "contact_name", "subject", "message_type", "status", "body_preview"]
                available_columns = [col for col in display_columns if col in filtered_conversations.columns]

                st.dataframe(
                    filtered_conversations[available_columns].head(20),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No conversations match the selected filters")
        else:
            st.info("No conversations found. Email polling may not be active or no emails have been received.")

    with tab5:
        st.header("📝 Content Management")

        # Content calendar generation
        st.subheader("📅 Content Calendar")
        col1, col2 = st.columns([2, 1])

        with col1:
            missions_data = system_data.get("missions", [])
            if missions_data:
                mission_options = {f"{mission.get('business_goal', 'Unknown')} (ID: {mission.get('id')})": mission.get('id')
                                for mission in missions_data}
                selected_mission = st.selectbox("Select mission for content calendar:", list(mission_options.keys()))

        with col2:
            if st.button("🎯 Generate 30-Day Calendar"):
                if missions_data and selected_mission:
                    mission_id = mission_options[selected_mission]
                    try:
                        response = requests.post(f"{dashboard.api_base_url}/content/calendar/generate",
                                               params={"mission_id": mission_id})
                        if response.status_code == 200:
                            st.success("Content calendar generation started!")
                            st.info("Check the Live Logs tab to monitor progress.")
                        else:
                            st.error("Failed to generate content calendar")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("Please select a mission")

        # Display content calendar
        st.subheader("📋 Content Calendar Items")
        try:
            response = requests.get(f"{dashboard.api_base_url}/content/calendar")
            if response.status_code == 200:
                content_data = response.json()
                content_items = content_data.get("content_items", [])

                if content_items:
                    df_content = pd.DataFrame(content_items)

                    # Content filters
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        status_filter = st.selectbox("Filter by Status", ["All"] + list(df_content["status"].unique()) if "status" in df_content.columns else ["All"])
                    with col2:
                        type_filter = st.selectbox("Filter by Type", ["All"] + list(df_content["content_type"].unique()) if "content_type" in df_content.columns else ["All"])
                    with col3:
                        platform_filter = st.selectbox("Filter by Platform", ["All"] + list(df_content["platform"].unique()) if "platform" in df_content.columns else ["All"])

                    # Apply filters
                    filtered_content = df_content.copy()
                    if status_filter != "All" and "status" in df_content.columns:
                        filtered_content = filtered_content[filtered_content["status"] == status_filter]
                    if type_filter != "All" and "content_type" in df_content.columns:
                        filtered_content = filtered_content[filtered_content["content_type"] == type_filter]
                    if platform_filter != "All" and "platform" in df_content.columns:
                        filtered_content = filtered_content[filtered_content["platform"] == platform_filter]

                    # Display content items
                    if not filtered_content.empty:
                        for _, content in filtered_content.iterrows():
                            with st.expander(f"📝 {content.get('title', 'Untitled')} - {content.get('status', 'draft').upper()}"):
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.write(f"**Type:** {content.get('content_type', 'N/A')}")
                                    st.write(f"**Platform:** {content.get('platform', 'N/A')}")
                                    st.write(f"**Topic:** {content.get('topic', 'N/A')}")
                                    st.write(f"**Scheduled:** {content.get('scheduled_date', 'N/A')}")
                                    if content.get('content_body'):
                                        st.text_area("Content Preview:", content['content_body'][:500] + "..." if len(content.get('content_body', '')) > 500 else content.get('content_body', ''), height=100, disabled=True)

                                with col2:
                                    if content.get('status') == 'draft' and not content.get('content_body'):
                                        if st.button(f"✍️ Generate Content", key=f"gen_{content['id']}"):
                                            try:
                                                response = requests.post(f"{dashboard.api_base_url}/content/{content['id']}/generate")
                                                if response.status_code == 200:
                                                    st.success("Content generation started!")
                                                    st.rerun()
                                                else:
                                                    st.error("Failed to generate content")
                                            except Exception as e:
                                                st.error(f"Error: {e}")

                                    elif content.get('status') == 'draft' and content.get('content_body'):
                                        if st.button(f"✅ Approve", key=f"approve_{content['id']}"):
                                            try:
                                                response = requests.post(f"{dashboard.api_base_url}/content/{content['id']}/approve")
                                                if response.status_code == 200:
                                                    st.success("Content approved!")
                                                    st.rerun()
                                                else:
                                                    st.error("Failed to approve content")
                                            except Exception as e:
                                                st.error(f"Error: {e}")
                    else:
                        st.info("No content items match the selected filters")
                else:
                    st.info("No content calendar items found. Generate a content calendar to get started!")
            else:
                st.error("Failed to fetch content calendar")
        except Exception as e:
            st.error(f"Error fetching content: {e}")

    with tab6:
        st.header("📦 Fulfillment Management")

        # Deal closure section
        st.subheader("💰 Deal Management")
        col1, col2 = st.columns([2, 1])

        with col1:
            leads_data = system_data.get("leads", [])
            if leads_data:
                # Filter leads that can be closed (qualified, negotiating, etc.)
                closeable_leads = [lead for lead in leads_data if lead.get('status') in ['qualified', 'negotiating', 'proposal_sent']]
                if closeable_leads:
                    lead_options = {f"{lead.get('company_name', 'Unknown')} - {lead.get('status', 'unknown')} (ID: {lead.get('id')})": lead.get('id')
                                  for lead in closeable_leads}
                    selected_lead = st.selectbox("Select lead to close deal:", list(lead_options.keys()))
                else:
                    st.info("No leads available for deal closure")

        with col2:
            if leads_data and 'selected_lead' in locals():
                if st.button("🎉 Close Deal"):
                    lead_id = lead_options[selected_lead]
                    try:
                        response = requests.post(f"{dashboard.api_base_url}/lead/{lead_id}/close_deal")
                        if response.status_code == 200:
                            st.success("Deal closed! Fulfillment process initiated.")
                            st.rerun()
                        else:
                            st.error("Failed to close deal")
                    except Exception as e:
                        st.error(f"Error: {e}")

        # Fulfillment projects display
        st.subheader("📋 Fulfillment Projects")
        try:
            response = requests.get(f"{dashboard.api_base_url}/fulfillment/projects")
            if response.status_code == 200:
                projects_data = response.json()
                projects = projects_data.get("projects", [])

                if projects:
                    df_projects = pd.DataFrame(projects)

                    # Project filters
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        status_filter = st.selectbox("Filter by Status", ["All"] + list(df_projects["status"].unique()) if "status" in df_projects.columns else ["All"], key="proj_status")
                    with col2:
                        type_filter = st.selectbox("Filter by Type", ["All"] + list(df_projects["project_type"].unique()) if "project_type" in df_projects.columns else ["All"], key="proj_type")
                    with col3:
                        deliverable_filter = st.selectbox("Filter by Deliverable", ["All"] + list(df_projects["deliverable_type"].unique()) if "deliverable_type" in df_projects.columns else ["All"], key="proj_deliverable")

                    # Apply filters
                    filtered_projects = df_projects.copy()
                    if status_filter != "All" and "status" in df_projects.columns:
                        filtered_projects = filtered_projects[filtered_projects["status"] == status_filter]
                    if type_filter != "All" and "project_type" in df_projects.columns:
                        filtered_projects = filtered_projects[filtered_projects["project_type"] == type_filter]
                    if deliverable_filter != "All" and "deliverable_type" in df_projects.columns:
                        filtered_projects = filtered_projects[filtered_projects["deliverable_type"] == deliverable_filter]

                    # Display projects
                    if not filtered_projects.empty:
                        for _, project in filtered_projects.iterrows():
                            with st.expander(f"📦 {project.get('project_title', 'Untitled Project')} - {project.get('status', 'unknown').upper()}"):
                                col1, col2 = st.columns([2, 1])
                                with col1:
                                    st.write(f"**Company:** {project.get('company_name', 'N/A')}")
                                    st.write(f"**Type:** {project.get('project_type', 'N/A')}")
                                    st.write(f"**Deliverable:** {project.get('deliverable_type', 'N/A')}")
                                    st.write(f"**Status:** {project.get('status', 'N/A')}")
                                    if project.get('project_description'):
                                        st.write(f"**Description:** {project['project_description']}")
                                    if project.get('estimated_completion'):
                                        st.write(f"**Est. Completion:** {project['estimated_completion']}")
                                    if project.get('deliverable_path'):
                                        st.write(f"**Deliverable Path:** {project['deliverable_path']}")

                                with col2:
                                    if project.get('project_type') == 'external' and project.get('freelancer_brief'):
                                        if st.button(f"📋 View Brief", key=f"brief_{project['id']}"):
                                            st.text_area("Freelancer Brief:", project['freelancer_brief'], height=200, disabled=True)
                    else:
                        st.info("No fulfillment projects match the selected filters")
                else:
                    st.info("No fulfillment projects found. Close some deals to see fulfillment projects!")
            else:
                st.error("Failed to fetch fulfillment projects")
        except Exception as e:
            st.error(f"Error fetching projects: {e}")

        # Manual fulfillment triggers
        st.subheader("🚀 Manual Fulfillment")
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Internal Fulfillment**")
            if leads_data:
                closed_leads = [lead for lead in leads_data if lead.get('status') == 'deal_closed']
                if closed_leads:
                    lead_options_internal = {f"{lead.get('company_name', 'Unknown')} (ID: {lead.get('id')})": lead.get('id')
                                           for lead in closed_leads}
                    selected_lead_internal = st.selectbox("Select lead for internal fulfillment:", list(lead_options_internal.keys()), key="internal_lead")

                    deliverable_type = st.selectbox("Deliverable Type:", ["pdf_report", "python_script", "marketing_plan", "business_plan"], key="internal_deliverable")

                    if st.button("🎯 Start Internal Fulfillment"):
                        lead_id = lead_options_internal[selected_lead_internal]
                        try:
                            response = requests.post(f"{dashboard.api_base_url}/fulfillment/internal",
                                                   json={"lead_id": lead_id, "project_requirements": {"deliverable_type": deliverable_type}})
                            if response.status_code == 200:
                                st.success("Internal fulfillment started!")
                                st.rerun()
                            else:
                                st.error("Failed to start internal fulfillment")
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.info("No closed deals available for internal fulfillment")

        with col2:
            st.write("**External Fulfillment**")
            if leads_data:
                closed_leads = [lead for lead in leads_data if lead.get('status') == 'deal_closed']
                if closed_leads:
                    lead_options_external = {f"{lead.get('company_name', 'Unknown')} (ID: {lead.get('id')})": lead.get('id')
                                           for lead in closed_leads}
                    selected_lead_external = st.selectbox("Select lead for external fulfillment:", list(lead_options_external.keys()), key="external_lead")

                    project_type = st.selectbox("Project Type:", ["consulting", "development", "design", "marketing"], key="external_type")
                    timeline = st.selectbox("Timeline:", ["1 week", "2 weeks", "1 month", "2 months"], key="external_timeline")

                    if st.button("📋 Generate Freelancer Brief"):
                        lead_id = lead_options_external[selected_lead_external]
                        try:
                            response = requests.post(f"{dashboard.api_base_url}/fulfillment/external",
                                                   json={"lead_id": lead_id, "project_requirements": {"project_type": project_type, "timeline": timeline}})
                            if response.status_code == 200:
                                st.success("Freelancer brief generation started!")
                                st.rerun()
                            else:
                                st.error("Failed to generate freelancer brief")
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.info("No closed deals available for external fulfillment")

    with tab7:
        st.header("🤖 Agent Status")
        
        # Agent status grid
        agents = [
            {"name": "MAESTRO", "role": "Orchestrator", "status": "active"},
            {"name": "ARCHITECT", "role": "Strategist", "status": "standby"},
            {"name": "SCOUT", "role": "Prospector", "status": "active"},
            {"name": "LOREWEAVER", "role": "Bard", "status": "standby"},
            {"name": "HERALD", "role": "Communicator", "status": "active"},
            {"name": "DIPLOMAT", "role": "Closer", "status": "standby"},
            {"name": "QUARTERMASTER", "role": "Dispatcher", "status": "standby"},
            {"name": "ARTIFICER", "role": "Creator", "status": "standby"},
            {"name": "WRENCH", "role": "Technician", "status": "monitoring"},
            {"name": "AEGIS", "role": "Guardian", "status": "active"}
        ]
        
        cols = st.columns(5)
        for i, agent in enumerate(agents):
            with cols[i % 5]:
                status_color = "🟢" if agent["status"] == "active" else "🟡" if agent["status"] == "standby" else "🔵"
                st.metric(
                    f"{status_color} {agent['name']}",
                    agent["role"],
                    agent["status"].upper()
                )

    with tab8:
        st.header("🔧 Technician - Error Monitoring & Auto-Repair")

        # Error statistics
        col1, col2, col3, col4 = st.columns(4)

        try:
            # Get error statistics from API
            response = requests.get(f"{dashboard.api_base_url}/technician/stats")
            if response.status_code == 200:
                stats = response.json()

                with col1:
                    st.metric("Total Errors", stats.get("total_errors", 0))
                with col2:
                    st.metric("Resolved Errors", stats.get("resolved_errors", 0),
                             delta=f"{stats.get('resolved_errors', 0) - stats.get('escalated_errors', 0)}")
                with col3:
                    st.metric("Escalated Errors", stats.get("escalated_errors", 0))
                with col4:
                    sandbox_status = "🟢 Active" if stats.get("sandbox_enabled", False) else "🔴 Disabled"
                    st.metric("Sandbox Status", sandbox_status)
            else:
                st.warning("Unable to fetch technician statistics")
        except Exception as e:
            st.error(f"Error fetching technician stats: {e}")

        # Error reports section
        st.subheader("📋 Recent Error Reports")

        try:
            # Get recent error reports
            response = requests.get(f"{dashboard.api_base_url}/technician/reports")
            if response.status_code == 200:
                reports = response.json()

                if reports:
                    # Create DataFrame for display
                    df_reports = pd.DataFrame(reports)

                    # Display reports table
                    st.dataframe(
                        df_reports[['timestamp', 'agent_name', 'error_category', 'error_severity', 'resolved', 'escalated']],
                        use_container_width=True
                    )

                    # Report details
                    if st.checkbox("Show Report Details"):
                        selected_report = st.selectbox("Select Report:",
                                                     [f"{r['report_id'][:8]} - {r['agent_name']} - {r['error_category']}"
                                                      for r in reports])

                        if selected_report:
                            report_id = selected_report.split(' - ')[0]
                            report = next((r for r in reports if r['report_id'].startswith(report_id)), None)

                            if report:
                                st.json(report)
                else:
                    st.info("No error reports found")
            else:
                st.warning("Unable to fetch error reports")
        except Exception as e:
            st.error(f"Error fetching reports: {e}")

        # Manual intervention queue
        st.subheader("🚨 Manual Intervention Queue")

        try:
            # Get escalated errors requiring human intervention
            response = requests.get(f"{dashboard.api_base_url}/technician/escalated")
            if response.status_code == 200:
                escalated = response.json()

                if escalated:
                    for error in escalated:
                        with st.expander(f"🚨 {error['agent_name']} - {error['error_category']} ({error['timestamp']})"):
                            st.write(f"**Error:** {error['exception_message']}")
                            st.write(f"**Severity:** {error['error_severity']}")
                            st.write(f"**Fix Attempts:** {len(error.get('fix_attempts', []))}")

                            if st.button(f"Mark Resolved", key=f"resolve_{error['report_id']}"):
                                # Mark error as resolved
                                resolve_response = requests.post(f"{dashboard.api_base_url}/technician/resolve/{error['report_id']}")
                                if resolve_response.status_code == 200:
                                    st.success("Error marked as resolved")
                                    st.rerun()
                                else:
                                    st.error("Failed to mark error as resolved")
                else:
                    st.success("✅ No errors requiring manual intervention")
            else:
                st.warning("Unable to fetch escalated errors")
        except Exception as e:
            st.error(f"Error fetching escalated errors: {e}")

        # Error category breakdown
        st.subheader("📊 Error Category Breakdown")

        try:
            response = requests.get(f"{dashboard.api_base_url}/technician/stats")
            if response.status_code == 200:
                stats = response.json()
                by_category = stats.get("by_category", {})

                if by_category:
                    # Create pie chart
                    fig = px.pie(
                        values=list(by_category.values()),
                        names=list(by_category.keys()),
                        title="Error Distribution by Category"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No error category data available")
        except Exception as e:
            st.error(f"Error creating category chart: {e}")

    # Auto-refresh
    if auto_refresh:
        time.sleep(5)
        st.rerun()

if __name__ == "__main__":
    main()
