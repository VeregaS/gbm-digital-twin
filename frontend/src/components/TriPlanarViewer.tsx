import {
  useMemo,
  useState,
} from "react";

import {
  viewerSliceUrl,
} from "../api/client";

import type {
  ViewerPlane,
  ViewerPlaneMetadata,
  ViewerVolumeMetadata,
} from "../api/types";


type TriPlanarViewerProps = {
  patientId: number;
  timepointName: string;

  metadata: ViewerVolumeMetadata;

  overlayGtv: boolean;
};


type SliceIndices = Record<
  ViewerPlane,
  number
>;


const planes: ViewerPlane[] = [
  "axial",
  "coronal",
  "sagittal",
];


function initialIndices(
  metadata: ViewerVolumeMetadata,
): SliceIndices {
  const result: SliceIndices = {
    axial: 0,
    coronal: 0,
    sagittal: 0,
  };

  for (
    const plane
    of metadata.planes
  ) {
    result[
      plane.name
    ] = plane.default_index;
  }

  return result;
}


function TriPlanarViewer({
  patientId,
  timepointName,
  metadata,
  overlayGtv,
}: TriPlanarViewerProps) {
  const [
    indices,
    setIndices,
  ] = useState<SliceIndices>(
    () =>
      initialIndices(
        metadata,
      ),
  );


  const planeMetadata =
    useMemo(
      () => {
        const mapping =
          new Map<
            ViewerPlane,
            ViewerPlaneMetadata
          >();

        for (
          const item
          of metadata.planes
        ) {
          mapping.set(
            item.name,
            item,
          );
        }

        return mapping;
      },
      [
        metadata,
      ],
    );


  function changeSlice(
    plane: ViewerPlane,
    value: number,
  ) {
    setIndices(
      (current) => ({
        ...current,
        [plane]: value,
      }),
    );
  }


  return (
    <div className="tri-planar-viewer">
      {planes.map(
        (plane) => {
          const info =
            planeMetadata.get(
              plane,
            );

          if (!info) {
            return null;
          }

          return (
            <SliceViewport
              key={plane}
              primary={
                plane === "axial"
              }
              patientId={
                patientId
              }
              timepointName={
                timepointName
              }
              plane={plane}
              index={
                indices[
                  plane
                ]
              }
              metadata={info}
              overlayGtv={
                overlayGtv
              }
              onChange={
                (value) =>
                  changeSlice(
                    plane,
                    value,
                  )
              }
            />
          );
        },
      )}
    </div>
  );
}


type SliceViewportProps = {
  primary: boolean;

  patientId: number;
  timepointName: string;

  plane: ViewerPlane;
  index: number;

  metadata: ViewerPlaneMetadata;

  overlayGtv: boolean;

  onChange: (
    value: number,
  ) => void;
};


function SliceViewport({
  primary,
  patientId,
  timepointName,
  plane,
  index,
  metadata,
  overlayGtv,
  onChange,
}: SliceViewportProps) {
  const imageUrl =
    viewerSliceUrl(
      patientId,
      timepointName,
      plane,
      index,
      overlayGtv,
    );

  return (
    <article
      className={
        primary
          ? (
            "tri-planar-card "
            + "primary"
          )
          : "tri-planar-card"
      }
    >
      <header className="tri-planar-card-header">
        <div>
          <strong>
            {
              capitalize(
                plane,
              )
            }
          </strong>

          <span>
            {
              timepointName
                .toUpperCase()
            }
          </span>
        </div>

        <span>
          {index}
          {" / "}
          {
            metadata.max_index
          }
        </span>
      </header>

      <div className="tri-planar-image-stage">
        <img
          src={imageUrl}
          alt={
            `${plane} MRI `
            + `slice ${index}`
          }
          draggable={false}
        />

        <span className="orientation-marker top">
          S
        </span>

        <span className="orientation-marker bottom">
          I
        </span>
      </div>

      <footer className="tri-planar-card-footer">
        <input
          type="range"
          min={0}
          max={
            metadata.max_index
          }
          value={index}
          onChange={
            (event) =>
              onChange(
                Number(
                  event.target.value,
                ),
              )
          }
        />
      </footer>
    </article>
  );
}


function capitalize(
  value: string,
): string {
  return (
    value.charAt(0)
      .toUpperCase()
    + value.slice(1)
  );
}


export default TriPlanarViewer;
