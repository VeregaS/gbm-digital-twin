declare module "@kitware/vtk.js/Filters/Core/PolyDataNormals" {
  import type {
    vtkAlgorithm,
    vtkObject,
  } from "@kitware/vtk.js/interfaces";

  type PolyDataNormals =
    vtkObject & vtkAlgorithm;

  type PolyDataNormalsInitialValues = {
    computeCellNormals?: boolean;
    computePointNormals?: boolean;
    featureAngle?: number;
    splitting?: boolean;
  };

  const vtkPolyDataNormals: {
    newInstance(
      initialValues?: PolyDataNormalsInitialValues,
    ): PolyDataNormals;

    extend(
      publicAPI: object,
      model: object,
      initialValues?: PolyDataNormalsInitialValues,
    ): void;
  };

  export default vtkPolyDataNormals;
}
