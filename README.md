# zoom-meeting-list
Work with user and meeting data from the Zoom API

## WIP
This is just a work in progress, so all the documentation below doesn't
quite apply yet. For development purposes, I've been manually acquiring the
token, and running it like so:

    ZOOM_TOKEN="ey..." bin/zml.sh

## Deployment

### Pushing Docker containers to local registry in Kubernetes
Here are some commands to get the Docker container pushed to our Docker
register in our Kubernetes cluster:

    kubectl -n kube-system port-forward $(kubectl get pods --namespace kube-system -l "app=docker-registry,release=docker-registry" -o jsonpath="{.items[0].metadata.name}") 5000:5000 &
    docker tag wipac/zml:0.0.x localhost:5000/wipac/zml:0.0.x
    docker push localhost:5000/wipac/zml:0.0.x

## Development

### Establishing a development environment
Follow these steps to get a development environment for zoom-meeting-list:

    cd ~/projects
    git clone git@github.com:WIPACrepo/zoom-meeting-list.git
    cd zoom-meeting-list
    python3.7 -m venv ./env
    source env/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

### Updating requirements.txt after a pip install
If you install a new package using `pip install cool-pkg-here` then
be sure to update the `requirements.txt` file with the following
command:

    pip freeze --all >requirements.txt

If you experience the bug in Debian/Ubuntu's virtualenv binary that includes
`pkg-resources==0.0.0` in `pip freeze`, the following command can help as
a quick hack:

    pip freeze --all | grep -v pkg-resources== >requirements.txt

But to fix it long-term, you'll need to use the right command to create the
virtual environment:

    virtualenv -p python3 env               # this is the bad line
    python3 -m virtualenv -p python3 env    # this is the better line

### Helper script
There is a helper script `snake` that defines some common project
tasks.

    Try one of the following tasks:

    snake check                # Check dependency package versions
    snake circleci             # Perform CI build and test
    snake clean                # Remove build cruft
    snake coverage             # Perform coverage analysis
    snake dist                 # Create a distribution tarball and wheel
    snake docker               # Create a docker container
    snake lint                 # Run static analysis tools
    snake rebuild              # Test and lint the module
    snake test                 # Test the module

The task `rebuild` doesn't really build (no need to compile Python),
but it does run static analysis tools and unit/integration tests.

### Bumping to the next version
If you need to increase the version number of the project, don't
forget to edit the following:

    CHANGELOG.md
    zml/__init__.py
