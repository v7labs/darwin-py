import darwin.importer as importer
from darwin.client import Client
from darwin.importer import get_importer

DATASET_IDENTIFIER = "product-camera-team/xero-goat"
FORMAT_NAME = "pascal_voc"
ANNOTATION_PATHS = ["/Users/john/Desktop/pascal"]

client = Client.from_api_key("zCOGdus.PdY-kT07sKASoHsw8FmlczMRDKw532Uz")
dataset = client.get_remote_dataset(dataset_identifier=DATASET_IDENTIFIER)
parser = get_importer(FORMAT_NAME)
importer.import_annotations(dataset, parser, ANNOTATION_PATHS, append=False)
