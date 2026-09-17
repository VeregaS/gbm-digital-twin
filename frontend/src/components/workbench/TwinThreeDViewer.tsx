import "@kitware/vtk.js/Rendering/Profiles/Geometry";

import vtkPolyData from "@kitware/vtk.js/Common/DataModel/PolyData";
import vtkPolyDataNormals from "@kitware/vtk.js/Filters/Core/PolyDataNormals";
import vtkActor from "@kitware/vtk.js/Rendering/Core/Actor";
import vtkMapper from "@kitware/vtk.js/Rendering/Core/Mapper";
import vtkGenericRenderWindow from "@kitware/vtk.js/Rendering/Misc/GenericRenderWindow";

import {
  Rotate3D,
  RotateCcw,
} from "lucide-react";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  fetchTwin3DScene,
} from "../../api/twin";

import type {
  Twin3DScene,
} from "../../api/twin";

import type {
  SurfaceMesh,
} from "../../api/types";


type TwinThreeDViewerProps = {
  patientId: number;
};


type SceneRequestState =
  | {
      patientId: number;
      status: "success";
      scene: Twin3DScene;
    }
  | {
      patientId: number;
      status: "error";
      error: string;
    };


type VtkActor = ReturnType<
  typeof vtkActor.newInstance
>;


type SceneActor = {
  actor: VtkActor;

  mapper: ReturnType<
    typeof vtkMapper.newInstance
  >;

  normals: ReturnType<
    typeof vtkPolyDataNormals.newInstance
  >;

  polyData: ReturnType<
    typeof vtkPolyData.newInstance
  >;
};


type ActorStyle = {
  color: [
    number,
    number,
    number,
  ];

  opacity: number;

  ambient: number;
  diffuse: number;
  specular: number;
  specularPower: number;
};


type LayerKey =
  | "brain"
  | "observed"
  | "twin"
  | "persistence"
  | "volumeBaseline";


type ActorMap = Record<
  LayerKey,
  VtkActor | null
>;


type SceneBounds = [
  number,
  number,
  number,
  number,
  number,
  number,
];


function emptyActorMap():
ActorMap {
  return {
    brain: null,
    observed: null,
    twin: null,
    persistence: null,
    volumeBaseline: null,
  };
}


function createPolyData(
  mesh: SurfaceMesh,
): ReturnType<
  typeof vtkPolyData.newInstance
> {
  const polyData =
    vtkPolyData.newInstance();

  polyData
    .getPoints()
    .setData(
      new Float32Array(
        mesh.vertices,
      ),
      3,
    );

  const triangleCount =
    mesh.triangles.length / 3;

  const cells =
    new Uint32Array(
      triangleCount * 4,
    );

  for (
    let triangle = 0;
    triangle < triangleCount;
    triangle += 1
  ) {
    const sourceIndex =
      triangle * 3;

    const targetIndex =
      triangle * 4;

    cells[targetIndex] = 3;

    cells[
      targetIndex + 1
    ] = (
      mesh.triangles[
        sourceIndex
      ]
    );

    cells[
      targetIndex + 2
    ] = (
      mesh.triangles[
        sourceIndex + 1
      ]
    );

    cells[
      targetIndex + 3
    ] = (
      mesh.triangles[
        sourceIndex + 2
      ]
    );
  }

  polyData
    .getPolys()
    .setData(
      cells,
    );

  polyData.modified();

  return polyData;
}


function createActor(
  mesh: SurfaceMesh,
  style: ActorStyle,
): SceneActor {
  const polyData =
    createPolyData(
      mesh,
    );

  const normals =
    vtkPolyDataNormals
    .newInstance({
      featureAngle: 60,
      splitting: false,
    });

  normals.setInputData(
    polyData,
  );

  const mapper =
    vtkMapper.newInstance();

  mapper.setInputConnection(
    normals.getOutputPort(),
  );

  const actor =
    vtkActor.newInstance();

  actor.setMapper(
    mapper,
  );

  const property =
    actor.getProperty();

  property.setColor(
    style.color[0],
    style.color[1],
    style.color[2],
  );

  property.setOpacity(
    style.opacity,
  );

  property
    .setInterpolationToPhong();

  property.setAmbient(
    style.ambient,
  );

  property.setDiffuse(
    style.diffuse,
  );

  property.setSpecular(
    style.specular,
  );

  property.setSpecularPower(
    style.specularPower,
  );

  return {
    actor,
    mapper,
    normals,
    polyData,
  };
}


function sceneBounds(
  scene: Twin3DScene,
): SceneBounds {
  const candidates = [
    scene.brain,
    scene.observed,
    scene.twin,
    scene.persistence,
    scene.volume_baseline,
  ];

  for (
    const mesh
    of candidates
  ) {
    if (
      mesh.vertex_count > 0
    ) {
      return mesh.bounds;
    }
  }

  return [
    0,
    1,
    0,
    1,
    0,
    1,
  ];
}


function setClinicalCamera(
  scene: Twin3DScene,
  genericRenderWindow: ReturnType<
    typeof vtkGenericRenderWindow.newInstance
  >,
): void {
  const renderer =
    genericRenderWindow
    .getRenderer();

  const renderWindow =
    genericRenderWindow
    .getRenderWindow();

  const camera =
    renderer
    .getActiveCamera();

  const bounds =
    sceneBounds(
      scene,
    );

  const centerX =
    (
      bounds[0]
      + bounds[1]
    ) / 2;

  const centerY =
    (
      bounds[2]
      + bounds[3]
    ) / 2;

  const centerZ =
    (
      bounds[4]
      + bounds[5]
    ) / 2;

  const sizeX =
    bounds[1]
    - bounds[0];

  const sizeY =
    bounds[3]
    - bounds[2];

  const sizeZ =
    bounds[5]
    - bounds[4];

  const diagonal =
    Math.sqrt(
      sizeX * sizeX
      + sizeY * sizeY
      + sizeZ * sizeZ,
    );

  const distance =
    Math.max(
      diagonal * 2,
      1,
    );

  camera.setFocalPoint(
    centerX,
    centerY,
    centerZ,
  );

  camera.setPosition(
    centerX,
    centerY - distance,
    centerZ,
  );

  camera.setViewUp(
    0,
    0,
    1,
  );

  camera
    .orthogonalizeViewUp();

  renderer.resetCamera(
    bounds,
  );

  renderer
    .resetCameraClippingRange();

  renderWindow.render();
}


function TwinThreeDViewer({
  patientId,
}: TwinThreeDViewerProps) {
  const containerRef =
    useRef<HTMLDivElement | null>(
      null,
    );

  const actorsRef =
    useRef<ActorMap>(
      emptyActorMap(),
    );

  const renderWindowRef =
    useRef<
      ReturnType<
        typeof vtkGenericRenderWindow.newInstance
      > | null
    >(null);

  const [
    sceneRequest,
    setSceneRequest,
  ] = useState<
    SceneRequestState | null
  >(null);

  const [
    showBrain,
    setShowBrain,
  ] = useState(
    true,
  );

  const [
    showObserved,
    setShowObserved,
  ] = useState(
    true,
  );

  const [
    showTwin,
    setShowTwin,
  ] = useState(
    true,
  );

  const [
    showPersistence,
    setShowPersistence,
  ] = useState(
    false,
  );

  const [
    showVolumeBaseline,
    setShowVolumeBaseline,
  ] = useState(
    false,
  );

  const currentSceneRequest =
    sceneRequest?.patientId
    === patientId
      ? sceneRequest
      : null;

  const scene =
    currentSceneRequest?.status
    === "success"
      ? currentSceneRequest.scene
      : null;

  const error =
    currentSceneRequest?.status
    === "error"
      ? currentSceneRequest.error
      : null;

  const loading =
    currentSceneRequest === null;

  const resetCamera =
    useCallback(
      () => {
        if (
          scene === null
          || renderWindowRef.current
          === null
        ) {
          return;
        }

        setClinicalCamera(
          scene,
          renderWindowRef.current,
        );
      },
      [
        scene,
      ],
    );

  useEffect(() => {
    let cancelled = false;

    fetchTwin3DScene(
      patientId,
    )
      .then(
        (result) => {
          if (cancelled) {
            return;
          }

          setSceneRequest({
            patientId,
            status: "success",
            scene: result,
          });
        },
      )
      .catch(
        (
          requestError:
            unknown,
        ) => {
          if (cancelled) {
            return;
          }

          setSceneRequest({
            patientId,
            status: "error",
            error:
              requestError
              instanceof Error
                ? requestError.message
                : (
                  "Failed to load "
                  + "Twin 3D scene"
                ),
          });
        },
      );

    return () => {
      cancelled = true;
    };
  }, [
    patientId,
  ]);

  useEffect(() => {
    const container =
      containerRef.current;

    if (
      container === null
      || scene === null
    ) {
      return;
    }

    const genericRenderWindow =
      vtkGenericRenderWindow
      .newInstance({
        background: [
          0.018,
          0.028,
          0.034,
        ],
      });

    renderWindowRef.current =
      genericRenderWindow;

    genericRenderWindow
      .setContainer(
        container,
      );

    genericRenderWindow.resize();

    const renderer =
      genericRenderWindow
      .getRenderer();

    const renderWindow =
      genericRenderWindow
      .getRenderWindow();

    const sceneActors:
      SceneActor[] = [];

    function addLayer(
      key: LayerKey,
      mesh: SurfaceMesh,
      style: ActorStyle,
    ): void {
      if (
        mesh.vertex_count <= 0
      ) {
        return;
      }

      const item =
        createActor(
          mesh,
          style,
        );

      actorsRef.current[
        key
      ] = item.actor;

      renderer.addActor(
        item.actor,
      );

      sceneActors.push(
        item,
      );
    }

    addLayer(
      "brain",
      scene.brain,
      {
        color: [
          0.74,
          0.81,
          0.84,
        ],
        opacity: 0.18,
        ambient: 0.25,
        diffuse: 0.72,
        specular: 0.20,
        specularPower: 24,
      },
    );

    addLayer(
      "observed",
      scene.observed,
      {
        color: [
          0.96,
          0.29,
          0.14,
        ],
        opacity: 0.88,
        ambient: 0.20,
        diffuse: 0.80,
        specular: 0.32,
        specularPower: 30,
      },
    );

    addLayer(
      "twin",
      scene.twin,
      {
        color: [
          0.15,
          0.44,
          0.94,
        ],
        opacity: 0.72,
        ambient: 0.24,
        diffuse: 0.76,
        specular: 0.32,
        specularPower: 28,
      },
    );

    addLayer(
      "persistence",
      scene.persistence,
      {
        color: [
          0.86,
          0.47,
          0.04,
        ],
        opacity: 0.46,
        ambient: 0.22,
        diffuse: 0.74,
        specular: 0.25,
        specularPower: 24,
      },
    );

    addLayer(
      "volumeBaseline",
      scene.volume_baseline,
      {
        color: [
          0.49,
          0.23,
          0.93,
        ],
        opacity: 0.46,
        ambient: 0.22,
        diffuse: 0.74,
        specular: 0.25,
        specularPower: 24,
      },
    );

    setClinicalCamera(
      scene,
      genericRenderWindow,
    );

    const resizeObserver =
      new ResizeObserver(
        () => {
          genericRenderWindow
            .resize();

          renderer
            .resetCameraClippingRange();

          renderWindow.render();
        },
      );

    resizeObserver.observe(
      container,
    );

    return () => {
      resizeObserver.disconnect();

      actorsRef.current =
        emptyActorMap();

      renderWindowRef.current =
        null;

      for (
        const item
        of sceneActors
      ) {
        renderer.removeActor(
          item.actor,
        );

        item.actor.delete();
        item.mapper.delete();
        item.normals.delete();
        item.polyData.delete();
      }

      genericRenderWindow.delete();
    };
  }, [
    scene,
  ]);

  useEffect(() => {
    actorsRef.current.brain
      ?.setVisibility(
        showBrain,
      );

    actorsRef.current.observed
      ?.setVisibility(
        showObserved,
      );

    actorsRef.current.twin
      ?.setVisibility(
        showTwin,
      );

    actorsRef.current.persistence
      ?.setVisibility(
        showPersistence,
      );

    actorsRef.current.volumeBaseline
      ?.setVisibility(
        showVolumeBaseline,
      );

    const genericRenderWindow =
      renderWindowRef.current;

    if (
      genericRenderWindow
      !== null
    ) {
      genericRenderWindow
        .getRenderer()
        .resetCameraClippingRange();

      genericRenderWindow
        .getRenderWindow()
        .render();
    }
  }, [
    scene,
    showBrain,
    showObserved,
    showTwin,
    showPersistence,
    showVolumeBaseline,
  ]);

  if (loading) {
    return (
      <div
        className="three-d-state"
      >
        Loading Twin 3D scene…
      </div>
    );
  }

  if (error !== null) {
    return (
      <div
        className={
          "three-d-state error"
        }
      >
        <strong>
          Unable to build
          Twin 3D scene
        </strong>

        <span>
          {error}
        </span>
      </div>
    );
  }

  if (scene === null) {
    return (
      <div
        className="three-d-state"
      >
        No Twin 3D scene available
      </div>
    );
  }

  return (
    <div
      className="three-d-viewer"
    >
      <div
        ref={containerRef}
        className="vtk-container"
      />

      <div
        className="three-d-hud"
      >
        <div
          className="three-d-badge"
        >
          <Rotate3D
            size={14}
          />

          <span>
            Drag to rotate ·
            Wheel to zoom
          </span>
        </div>

        <div
          className="three-d-toolbar"
        >
          <button
            type="button"
            className={
              "three-d-reset-button"
            }
            onClick={
              resetCamera
            }
          >
            <RotateCcw
              size={13}
            />

            Reset
          </button>

          <div
            className="three-d-layers"
          >
            <LayerToggle
              label="Brain"
              checked={showBrain}
              color="#bdced6"
              onChange={
                setShowBrain
              }
            />

            <LayerToggle
              label="Observed t2"
              checked={
                showObserved
              }
              color="#f54a24"
              onChange={
                setShowObserved
              }
            />

            <LayerToggle
              label="Twin"
              checked={showTwin}
              color="#266ff0"
              onChange={
                setShowTwin
              }
            />

            <LayerToggle
              label="Persistence"
              checked={
                showPersistence
              }
              color="#db780a"
              onChange={
                setShowPersistence
              }
            />

            <LayerToggle
              label="Volume baseline"
              checked={
                showVolumeBaseline
              }
              color="#7d3bed"
              onChange={
                setShowVolumeBaseline
              }
            />
          </div>
        </div>
      </div>

      <div
        className={
          "three-d-orientation"
        }
      >
        <span
          className={
            "orientation-superior"
          }
        >
          S
        </span>

        <span
          className={
            "orientation-inferior"
          }
        >
          I
        </span>
      </div>

      <div
        className="three-d-stats"
      >
        <span>
          observed{" "}
          {
            scene.observed
            .triangle_count
            .toLocaleString()
          }
          {" tris"}
        </span>

        <span>
          twin{" "}
          {
            scene.twin
            .triangle_count
            .toLocaleString()
          }
          {" tris"}
        </span>

        <span>
          spacing{" "}
          {
            scene.spacing
            .map(
              (value) =>
                value.toFixed(1),
            )
            .join(" × ")
          }
          {" mm"}
        </span>
      </div>
    </div>
  );
}


type LayerToggleProps = {
  label: string;

  checked: boolean;

  color: string;

  onChange: (
    value: boolean,
  ) => void;
};


function LayerToggle({
  label,
  checked,
  color,
  onChange,
}: LayerToggleProps) {
  return (
    <label>
      <input
        type="checkbox"
        checked={checked}
        onChange={
          (event) =>
            onChange(
              event.target.checked,
            )
        }
      />

      <span
        className="layer-dot"
        style={{
          backgroundColor:
            color,
        }}
      />

      {label}
    </label>
  );
}


export default TwinThreeDViewer;