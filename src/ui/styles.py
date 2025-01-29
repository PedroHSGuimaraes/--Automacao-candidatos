# src/ui/styles.py

QUERY_STYLES = """
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #F0F2F6;
        border-radius: 4px;
        color: #000000;
        font-size: 14px;
        font-weight: 400;
        align-items: center;
        justify-content: center;
        padding: 0px 16px;
    }

    .stButton>button {
        width: 100%;
    }
</style>
"""

UPLOAD_STYLES = """
<style>
    .upload-section {
        border: 2px dashed #ccc;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        margin: 20px 0;
    }

    .success-message {
        color: #28a745;
        padding: 10px;
        border-radius: 4px;
        margin: 10px 0;
    }

    .error-message {
        color: #dc3545;
        padding: 10px;
        border-radius: 4px;
        margin: 10px 0;
    }
</style>
"""

VIEWER_STYLES = """
<style>
    .dataframe-container {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin: 15px 0;
    }

    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        text-align: center;
    }
</style>
"""