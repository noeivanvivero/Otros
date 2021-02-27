from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
import os

cog_key = '<use your own>'
cog_endpoint = '<use your own>'

print('Ready to use cognitive services at {} using key {}'.format(cog_endpoint, cog_key))

def image_description(image_stream):
    computervision_client = ComputerVisionClient(cog_endpoint, CognitiveServicesCredentials(cog_key))
    description = computervision_client.describe_image_in_stream(image_stream)
    return description

def image_anlaysis(image_stream):
    computervision_client = ComputerVisionClient(cog_endpoint, CognitiveServicesCredentials(cog_key))
    features = ['Description', 'Tags', 'Adult', 'Objects', 'Faces']
    analysis = computervision_client.analyze_image_in_stream(image_stream, visual_features=features)
    return analysis
