import dash
from dash import html, callback, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State


# Example data structure
candidates = [
    {"id": 1, "name": "Candidate A", "matched_drivers": [{"name": "Driver 1"}, {"name": "Driver 2"}]},
    {"id": 2, "name": "Candidate B", "matched_drivers": [{"name": "Driver 3"}, {"name": "Driver 4"}]},
]

# Function to create a button and collapse component for each candidate
def create_candidate_component(candidate):
    return html.Div([
        dbc.Button(
            candidate["name"],
            id=f"collapse-button-{candidate['id']}",
            className="mb-3",
            color="primary",
            n_clicks=0,
        ),
        dbc.Collapse(
            dbc.Card(dbc.CardBody([html.P(driver["name"]) for driver in candidate["matched_drivers"]])),
            id=f"collapse-{candidate['id']}",
            is_open=False,
        ),
    ])

# Create the components for all candidates
candidates_components = [create_candidate_component(candidate) for candidate in candidates]

# Layout
layout = html.Div(candidates_components)




@callback(
    [Output(f"collapse-{candidate['id']}", "is_open") for candidate in candidates],
    [Input(f"collapse-button-{candidate['id']}", "n_clicks") for candidate in candidates],
    [State(f"collapse-{candidate['id']}", "is_open") for candidate in candidates],
)
def toggle_collapse(*args):
    ctx = callback_context

    if not ctx.triggered:
        # If nothing was triggered, return the current state
        return [False for _ in candidates]
    else:
        # Find which button was clicked
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Extract the candidate id from the button id
        candidate_id = int(button_id.split("-")[-1])
        
        # Toggle the state of the corresponding collapse component
        return [not args[len(candidates) + i] if candidate['id'] == candidate_id else args[len(candidates) + i] for i, candidate in enumerate(candidates)]

# from dash import html, dcc, callback, Input, Output, State
# import dash_bootstrap_components as dbc
# from db.db_support import fetch_matched_drivers

# layout = html.Div([
#     # Add your layout components here
# ])

# @callback(
#     Output('match-details-container', 'children'), 
#     Input('drivers-to-match-store', 'data')
# )
# def update_match_details(kendra_ids):
#     if kendra_ids:
#         matched_drivers_df = fetch_matched_drivers(kendra_ids)
#         # Convert the DataFrame to editable forms or display components
#         # This part depends on how you want to display and edit the data
#         return html.Div([
#             # Create and return your display components based on matched_drivers_df
#         ])
#     return "No matched drivers found."
