# Creek Monitoring Chatbot

This chatbot has been integrated into your Creek Monitoring Dashboard to provide intelligent assistance with water quality data analysis.

## Features

🤖 **Intelligent Data Analysis**: Ask questions about water quality trends, site comparisons, and data interpretation

📊 **Real-time Data Access**: The chatbot has access to all your creek monitoring data including E. coli, pH, and turbidity measurements

🗺️ **Interactive Dashboard Integration**: Chatbot responses can trigger dashboard updates (e.g., selecting specific sites)

🔧 **Multiple Tools**: 
- Site information and comparisons
- Water quality summaries
- Trend analysis
- Measurement explanations
- EPA standard compliance checking

## Setup Instructions

### 1. Install Dependencies

The required packages have been added to `requirements.txt`. Install them with:

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

You need to set the following environment variables:

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

For deployment (e.g., Render), add this to your environment variables in the deployment settings.

### 3. Test the Chatbot

Run the test script to verify everything works:

```bash
python test_chatbot.py
```

### 4. Run the Dashboard

Start your dashboard as usual:

```bash
python app.py
```

## Usage

### In the Dashboard

1. **Chat Interface**: Located at the top of the dashboard
2. **Quick Actions**: Use the buttons for common queries:
   - "Water Quality Summary" - Get an overview of all sites
   - "Compare Sites" - Compare E. coli levels across sites
   - "Available Sites" - List all monitoring locations

3. **Custom Questions**: Type any question about:
   - Specific sites: "Tell me about Peavine creek/Old briarcliff way"
   - Trends: "Show me E. coli trends for the last 8 weeks at Lullwater creek"
   - Comparisons: "Which site has the highest turbidity?"
   - Standards: "Are any sites above EPA standards?"

### Example Questions

- "What's the current water quality at Peavine creek/Oxford Rd NE?"
- "Compare pH levels across all sites"
- "Show me trends for turbidity at Lullwater creek"
- "Which sites are above EPA standards for E. coli?"
- "What does a pH of 7.2 mean for water quality?"
- "Give me a summary of the worst performing sites"

## Technical Details

### Architecture

- **LangChain**: Powers the conversational AI with OpenAI GPT-3.5-turbo
- **Tools**: Custom tools for data access and analysis
- **Memory**: Conversation history maintained for context
- **Integration**: Seamlessly integrated with Dash callbacks

### Data Access

The chatbot has access to:
- All monitoring site data (E. coli, pH, turbidity)
- Site location information
- Historical trends and comparisons
- EPA standards and health implications

### Customization

To add more functionality:

1. **New Tools**: Add methods to `CreekDataTools` class in `chatbot.py`
2. **Enhanced Prompts**: Modify the system prompt in `CreekChatbot.__init__()`
3. **Additional Data**: Extend the data processing in `app.py`

## Troubleshooting

### Common Issues

1. **"OPENAI_API_KEY not set"**
   - Ensure your environment variable is set correctly
   - Check deployment environment variables

2. **"No data available"**
   - Verify data files are in the correct location
   - Check file paths in the data loading section

3. **Chatbot not responding**
   - Check OpenAI API quota and billing
   - Verify internet connectivity
   - Check console for error messages

### Debug Mode

Enable verbose logging by setting `verbose=True` in the `AgentExecutor` initialization in `chatbot.py`.

## Future Enhancements

- **Additional Knowledge Base**: Integrate markdown/CSV files with interpretation guidelines
- **Advanced Analytics**: Add statistical analysis and forecasting
- **Alert System**: Notify users of concerning water quality changes
- **Multi-language Support**: Support for different languages
- **Voice Interface**: Add speech-to-text capabilities

## Support

For issues or questions about the chatbot integration, check:
1. The console output for error messages
2. OpenAI API status and billing
3. Data file integrity and format 