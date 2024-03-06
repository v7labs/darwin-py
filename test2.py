import darwin.importer as importer
from darwin.client import Client
from darwin.importer import get_importer

DATASET_IDENTIFIER = "v7-john/bbox"
FORMAT_NAME = "pascal_voc"
ANNOTATION_PATHS = ["/Users/john/Desktop/pascal"]

client = Client.local()
dataset = client.get_remote_dataset(dataset_identifier=DATASET_IDENTIFIER)
parser = get_importer(FORMAT_NAME)
importer.import_annotations(dataset, parser, ANNOTATION_PATHS, append=True)
