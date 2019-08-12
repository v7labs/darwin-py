import multiprocessing as mp

from darwin import Client

"""
Minimal script to showcase and download a remote dataset on your file system using the Darwin-cli
"""
# Dataset info
OUTPUT_PATH="/path/darwin/"
DATASET_SLUG = 'my_slug'
TEAM_SLUG = 'my_team'
# Auth
EMAIL="hello.world@v7labs.com"
PASSWORD="**********"

if __name__ == "__main__":

    client = Client.login(email=EMAIL,
                          password=PASSWORD,
                          projects_dir=OUTPUT_PATH)

    print(f"Existing teams slug (selected={TEAM_SLUG}):")
    teams = client.list_teams()
    for team in teams:
        print("\t", team.name ,f"({team.slug})")

    client.set_team(slug=TEAM_SLUG)

    print(f"Existing remote datasets (selected={DATASET_SLUG}):")
    for dataset in client.list_remote_datasets():
        print("\t", dataset.name, f"({dataset.slug})", dataset.image_count)

    def run(f): f()
    for dataset in client.list_remote_datasets():
        if DATASET_SLUG in dataset.slug:
            progress, _count = client.get_remote_dataset(slug=dataset.slug).pull()
            print(f"Start downloading...")
            with mp.Pool(mp.cpu_count()) as pool:
                pool.map(run, progress())

    print("done!")

