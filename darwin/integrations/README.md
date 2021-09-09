# Darwin Integrations

Darwin Integrations APIs enable users to integrate their models into the Darwin ecosystem.

## Requirements

- Implement an `Integration` class, inheriting from the `IntegrationStrategy` abstract class. Writing an `Integration` requires users to implement its `load`, `infer` and `train` methods, responsible respectively to load your model architecture and weights, sending a batch of files for inference, and train a new model.
- Make sure you keep your requirements tidy in a `requirements.txt`.
- Make sure you keep a list of classes your model was trained on in a `classes.txt` file.

## CLI

- Build the integration with `darwin integrations build . -t my-integration`.
  1. Sanity check
    - Load the model (no weights)
    - Send an image file for inference
  2. Pull base image from V7
  3. Install requirements
  4. Install gust
  5. Wrap around gust entrypoint
- Push the integration with `darwin integrations push my-integration --tag v1`. The integration will be stored in V7's private ECR repository, indexed by `/models/team-slug/my-integration`, and tagged as `:v1`.
- Register your integration with `darwin integrations register my-integration --name "My Integration" --image <image-url> --classes /path/to/classes.txt --weights /path/to/weights.pth`. Note that `<image-url>` is returned in the `push` step.
  1. Upload weights to S3
  2. Register ModelTemplate on Wind (name, image and classes)
  3. Register TrainedModel on Wind (name, image, classes and weights)
- Publish your integration, so everyone can use it `darwin integrations publish my-integration`.
  1. Mark TrainedModel as `public: true`