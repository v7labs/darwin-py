# LiDAR and multi-camera formats

`darwin.lidar` converts LiDAR datasets into Darwin uploads, converts their labels into Darwin 3D
annotations, and converts Darwin exports back into dataset formats.

- Darwin JSON 2.0 parsing and serialization keep `pointcloud` slots (their `metadata`:
  `coordinate_frame` and per-frame `timestamp` / `ego_pose`) and the five 3D annotation types
  `cuboid_3d`, `polyline_3d`, `polygon_3d`, `keypoint_3d` and `point_mask_3d`. A Darwin export
  parses and serializes back unchanged (`darwin.lidar.to_darwin_json`).
- `darwin dataset push` accepts `.pcd` (one frame, sensor frame) and `.lidar.zip` (a
  `darwin-lidar-scene` v2 package: per-frame PCDs, ego poses, per-frame camera JPEGs).
- Optional dependencies: `pip install "darwin-py[lidar]"`, or only what you need:
  `lidar_av2` (pyarrow), `lidar_pandaset` (pandas), `lidar_las` (laspy; `.laz` also needs `lazrs`).

## Workflow

```sh
# 1. raw dataset -> upload package
python -m darwin.lidar build nuscenes /data/nuscenes scene-0061 packages/
darwin dataset push my-dataset packages/scene-0061.lidar.zip

# 2. dataset labels -> Darwin JSON -> Darwin (classes are created when missing)
python -m darwin.lidar labels nuscenes /data/nuscenes/v1.0-mini -o labels/
darwin dataset import my-dataset darwin labels/
#    or in one step with the default options:
darwin dataset import my-dataset nuscenes /data/nuscenes/v1.0-mini

# 3. Darwin export -> dataset format
darwin dataset pull my-dataset:release
python -m darwin.lidar export kitti <release>/annotations -o kitti_labels/ --calib calib.txt
#    or with the default options:
darwin convert kitti_3d <release>/annotations kitti_labels/
```

Every command maps to a Python function with the same options
(`python -m darwin.lidar build kitti_raw -h`). Label importers name items like the builders do,
so the labels land on the uploaded packages. Point masks index points in file order, and every
builder keeps every point in file order.

## Supported formats

| Dataset | `build` (upload package) | `labels` / `darwin dataset import` | `export` / `darwin convert` |
|---|---|---|---|
| Point clouds: `.pcd` (ascii, binary, binary_compressed), KITTI `.bin`, `.ply`, `.npy`, `.las`/`.laz`, AV2 `.feather` | `pcd` (one cloud -> `.pcd`), `pointcloud` (folder -> `.lidar.zip`, `--poses` file -> world frame) | | |
| KITTI raw | `kitti_raw` (sensor frame, `--world` with OXTS) | `kitti_tracklets` (`tracklet_labels.xml`) / `kitti_3d` | `kitti` / `kitti_3d` |
| KITTI tracking | `kitti_tracking` | `kitti_tracking` (`label_02`) / `kitti_3d` | `kitti --tracking --calib` |
| KITTI object | `kitti_object` (one 1-frame package per frame) | `kitti` (`label_2`) / `kitti_3d` | `kitti --calib` |
| SemanticKITTI / KITTI odometry | `kitti_odometry` (world frame from `poses.txt` + `calib.txt`) | `semantic_kitti` (`.label` -> point masks) | `semantic_kitti` |
| nuScenes (no devkit) | `nuscenes` (LIDAR_TOP + 6 cameras, key frames at 2 Hz) | `nuscenes` (`sample_annotation`), `nuscenes_lidarseg` (lidarseg / `--panoptic`) | `nuscenes` (`sample_annotation`-like JSON) |
| Argoverse 2 sensor | `av2` (sweeps + 7 ring cameras) | `av2` (`annotations.feather`) / `argoverse2` | `av2` / `argoverse2` (`annotations.feather`, ego frame) |
| PandaSet | `pandaset` (both lidars, cameras) | `pandaset` (cuboids + semseg) | |
| ASAM OpenLABEL 1.0 | | `openlabel` (cuboid, poly3d, point3d; per-frame and static objects; coordinate systems and per-frame transforms) | `openlabel` |
| Ego-frame view of any Darwin export | | | `ego` / `lidar_ego` |

All of these are covered by round-trip tests on small synthetic datasets
(`tests/darwin/lidar`): dataset labels -> Darwin JSON -> dataset format gives back the original
labels (within float tolerance), and a Darwin LiDAR export parses and serializes unchanged.
They have not been run against the full public datasets.

## Coordinate frames

- Packages are in a `world` frame (the dataset's world/city/global frame translated so the first
  frame's ego position is the origin) when the dataset has poses, otherwise in the `sensor`
  frame of each sweep. The `ego_pose` of each frame (4x4, `scene <- ego`) is stored in the
  package and comes back in exports as slot `metadata.frames[t].ego_pose`.
- The ego frame is the dataset's own vehicle frame (KITTI: velodyne, nuScenes: ego, AV2:
  egovehicle, PandaSet: lidar pose), not lowered to the ground.
- `cuboid_3d`: `position` = center, `dimensions` x/y/z = length/width/height, `rotation` x/y/z =
  roll/pitch/yaw with `R = Rz(yaw) Ry(pitch) Rx(roll)`. Importers keep full rotations, so round
  trips are exact; the Darwin editor draws and edits yaw only.
- `darwin.lidar.to_ego_frame(cuboid, ego_pose)` / `to_scene_frame` convert one frame's geometry,
  and `yaw_only` drops roll and pitch.
- The scene origin is not stored, so exports are in the scene frame. Pass it back with
  `export nuscenes --origin X Y Z` to get global coordinates.

## Known limitations

- Waymo Open Dataset is not supported. v2 parquet stores LiDAR as range images. Turning them
  into points needs per-beam inclinations, extrinsics and, for the TOP lidar, per-pixel vehicle
  poses (rolling shutter). Cameras use a rolling-shutter model. Without real data we can't verify
  a tensorflow-free implementation.
- Supervisely point cloud episodes are not supported: their cuboid axis conventions could not be
  verified.
- Exporters use the frames present in the file. Darwin exports contain every frame of each
  annotation, interpolated ones included.
- KITTI: truncation, occlusion and 2D boxes are not imported. On export, alpha and the 2D box
  are recomputed from the 3D box.
- nuScenes uses key frames only (2 Hz, the labeled frames). Importing boxes and lidarseg onto
  the same item needs `--append` for the second import.
- PandaSet `.pkl.gz` files are pickles and can run code: use trusted data only. Cuboid
  attributes are not imported. Darwin yaw = PandaSet yaw + pi/2 and length = `dimensions.y`
  (from the devkit's geometry); the heading sign has not been checked against labeled data.
- OpenLABEL: point masks are not exported; 2D geometry and non-geometric object data are ignored.
- Instance ids need the Instance ID sub-type on the class. Classes the importer creates get it
  when their tracks carry instance ids; for existing classes, add it in Darwin first. Darwin
  creates new annotation ids on import.
- Large clouds: write aggregated maps in a spatial order so point masks stay compact.
