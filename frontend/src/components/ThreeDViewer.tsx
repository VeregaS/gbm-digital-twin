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
  fetchViewer3DScene,
} from "../api/client";

import type {
  SurfaceMesh,
  Viewer3DScene,
} from "../api/types";


type ThreeDViewerProps = {
  patientId: number;
  timepointName: string;
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


type SceneBounds = [
  number,
  number,
  number,
  number,
  number,
  number,
];


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

  const cells = new Uint32Array(
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

    cells[
      targetIndex
    ] = 3;

    cells[
      targetIndex + 1
    ] = mesh.triangles[
      sourceIndex
    ];

    cells[
      targetIndex + 2
    ] = mesh.triangles[
      sourceIndex + 1
    ];

    cells[
      targetIndex + 3
    ] = mesh.triangles[
      sourceIndex + 2
    ];
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
    vtkPolyDataNormals.newInstance({
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

  property.setInterpolationToPhong();

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
  scene: Viewer3DScene,
): SceneBounds {
  if (
    scene.brain.vertex_count
    > 0
  ) {
    return scene.brain.bounds;
  }

  if (
    scene.latent_outer.vertex_count
    > 0
  ) {
    return scene.latent_outer.bounds;
  }

  return scene.gtv.bounds;
}


function setClinicalCamera(
  scene: Viewer3DScene,
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
    renderer.getActiveCamera();

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

  camera.orthogonalizeViewUp();

  renderer.resetCamera(
    bounds,
  );

  renderer
    .resetCameraClippingRange();

  renderWindow.render();
}


function ThreeDViewer({
  patientId,
  timepointName,
}: ThreeDViewerProps) {
  const containerRef =
    useRef<HTMLDivElement | null>(
      null,
    );

  const actorsRef =
    useRef<{
      brain: VtkActor | null;
      gtv: VtkActor | null;
      latentOuter: VtkActor | null;
      latentCore: VtkActor | null;
    }>({
      brain: null,
      gtv: null,
      latentOuter: null,
      latentCore: null,
    });

  const renderWindowRef =
    useRef<
      ReturnType<
        typeof vtkGenericRenderWindow.newInstance
      > | null
    >(null);

  const [
    scene,
    setScene,
  ] = useState<
    Viewer3DScene | null
  >(null);

  const [
    loading,
    setLoading,
  ] = useState(
    true,
  );

  const [
    error,
    setError,
  ] = useState<
    string | null
  >(
    null,
  );

  const [
    showBrain,
    setShowBrain,
  ] = useState(
    true,
  );

  const [
    showGtv,
    setShowGtv,
  ] = useState(
    true,
  );

  const [
    showLatentOuter,
    setShowLatentOuter,
  ] = useState(
    true,
  );

  const [
    showLatentCore,
    setShowLatentCore,
  ] = useState(
    false,
  );


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

    setLoading(
      true,
    );

    setError(
      null,
    );

    fetchViewer3DScene(
      patientId,
      timepointName,
    )
      .then((result) => {
        if (!cancelled) {
          setScene(
            result,
          );
        }
      })
      .catch(
        (
          requestError: unknown,
        ) => {
          if (cancelled) {
            return;
          }

          setScene(
            null,
          );

          setError(
            requestError
              instanceof Error
              ? requestError.message
              : (
                "Failed to load "
                + "3D scene"
              ),
          );
        },
      )
      .finally(() => {
        if (!cancelled) {
          setLoading(
            false,
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [
    patientId,
    timepointName,
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


    if (
      scene.brain.vertex_count
      > 0
    ) {
      const item =
        createActor(
          scene.brain,
          {
            color: [
              0.74,
              0.81,
              0.84,
            ],
            opacity: 0.24,
            ambient: 0.25,
            diffuse: 0.72,
            specular: 0.20,
            specularPower: 24,
          },
        );

      item.actor.setVisibility(
        showBrain,
      );

      actorsRef.current.brain =
        item.actor;

      renderer.addActor(
        item.actor,
      );

      sceneActors.push(
        item,
      );
    }


    if (
      scene.latent_outer.vertex_count
      > 0
    ) {
      const item =
        createActor(
          scene.latent_outer,
          {
            color: [
              0.20,
              0.85,
              0.88,
            ],
            opacity: 0.20,
            ambient: 0.30,
            diffuse: 0.65,
            specular: 0.25,
            specularPower: 25,
          },
        );

      item.actor.setVisibility(
        showLatentOuter,
      );

      actorsRef.current
        .latentOuter =
        item.actor;

      renderer.addActor(
        item.actor,
      );

      sceneActors.push(
        item,
      );
    }


    if (
      scene.latent_core.vertex_count
      > 0
    ) {
      const item =
        createActor(
          scene.latent_core,
          {
            color: [
              0.68,
              0.48,
              0.95,
            ],
            opacity: 0.58,
            ambient: 0.25,
            diffuse: 0.75,
            specular: 0.30,
            specularPower: 28,
          },
        );

      item.actor.setVisibility(
        showLatentCore,
      );

      actorsRef.current
        .latentCore =
        item.actor;

      renderer.addActor(
        item.actor,
      );

      sceneActors.push(
        item,
      );
    }


    if (
      scene.gtv.vertex_count
      > 0
    ) {
      const item =
        createActor(
          scene.gtv,
          {
            color: [
              0.96,
              0.29,
              0.14,
            ],
            opacity: 0.90,
            ambient: 0.20,
            diffuse: 0.80,
            specular: 0.32,
            specularPower: 30,
          },
        );

      item.actor.setVisibility(
        showGtv,
      );

      actorsRef.current.gtv =
        item.actor;

      renderer.addActor(
        item.actor,
      );

      sceneActors.push(
        item,
      );
    }


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

      actorsRef.current = {
        brain: null,
        gtv: null,
        latentOuter: null,
        latentCore: null,
      };

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

    actorsRef.current.gtv
      ?.setVisibility(
        showGtv,
      );

    actorsRef.current.latentOuter
      ?.setVisibility(
        showLatentOuter,
      );

    actorsRef.current.latentCore
      ?.setVisibility(
        showLatentCore,
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
    showBrain,
    showGtv,
    showLatentOuter,
    showLatentCore,
  ]);


  if (loading) {
    return (
      <div className="three-d-state">
        Loading digital twin…
      </div>
    );
  }


  if (error !== null) {
    return (
      <div className="three-d-state error">
        <strong>
          Unable to build 3D scene
        </strong>

        <span>
          {error}
        </span>
      </div>
    );
  }


  if (scene === null) {
    return (
      <div className="three-d-state">
        No 3D scene available
      </div>
    );
  }


  return (
    <div className="three-d-viewer">
      <div
        ref={
          containerRef
        }
        className="vtk-container"
      />


      <div className="three-d-hud">
        <div className="three-d-badge">
          <Rotate3D
            size={14}
          />

          <span>
            Drag to rotate ·
            Wheel to zoom
          </span>
        </div>


        <div className="three-d-toolbar">
          <button
            type="button"
            className="three-d-reset-button"
            onClick={
              resetCamera
            }
          >
            <RotateCcw
              size={13}
            />

            Reset
          </button>


          <div className="three-d-layers">
            <label>
              <input
                type="checkbox"
                checked={
                  showBrain
                }
                onChange={
                  (event) =>
                    setShowBrain(
                      event.target
                        .checked,
                    )
                }
              />

              <span className="layer-dot brain" />

              Brain
            </label>


            <label>
              <input
                type="checkbox"
                checked={
                  showGtv
                }
                onChange={
                  (event) =>
                    setShowGtv(
                      event.target
                        .checked,
                    )
                }
              />

              <span className="layer-dot tumor" />

              GTV
            </label>


            <label>
              <input
                type="checkbox"
                checked={
                  showLatentOuter
                }
                onChange={
                  (event) =>
                    setShowLatentOuter(
                      event.target
                        .checked,
                    )
                }
              />

              <span className="layer-dot latent-outer" />

              Latent 0.2
            </label>


            <label>
              <input
                type="checkbox"
                checked={
                  showLatentCore
                }
                onChange={
                  (event) =>
                    setShowLatentCore(
                      event.target
                        .checked,
                    )
                }
              />

              <span className="layer-dot latent-core" />

              Latent 0.8
            </label>
          </div>
        </div>
      </div>


      <div className="three-d-orientation">
        <span className="orientation-superior">
          S
        </span>

        <span className="orientation-inferior">
          I
        </span>
      </div>


      <div className="three-d-stats">
        <span>
          latent width{" "}
          {
            scene.latent_width_mm
              .toFixed(1)
          }
          {" mm"}
        </span>

        <span>
          brain{" "}
          {
            scene.brain
              .triangle_count
              .toLocaleString()
          }
          {" tris"}
        </span>

        <span>
          GTV{" "}
          {
            scene.gtv
              .triangle_count
              .toLocaleString()
          }
          {" tris"}
        </span>
      </div>
    </div>
  );
}


export default ThreeDViewer;