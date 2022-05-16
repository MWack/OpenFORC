ref_dirs = [[e["D"], e["I"]] for e in dirs.to_py().values()]
if matrix_type == 'v':
    measurements = [e[i] for e in dirs.to_py().values() for i in ("x", "y", "z")]
else:
    measurements = [e["s"] for e in dirs.to_py().values()]
if tensor_type == 'p':
    dm = tf.makeDesignMatrix(ref_dirs, xyz=False)  # make scalar design matrix
    # calculate projected measurements
    measurements_projected = [
        tf.Proj_A_on_B_scalar(measurements[i * 3:i * 3 + 3], tf.DIL2XYZ(np.append(ref_dirs[i], 1))) for i in
        range(len(ref_dirs))]
    print(measurements_projected)
    tensor = tf.CalcAnisoTensor(dm, measurements_projected)
elif tensor_type == 's' or tensor_type == 'v':
    dm = tf.makeDesignMatrix(ref_dirs, xyz=(matrix_type == 'v'))
    tensor = tf.CalcAnisoTensor(dm, measurements)
elif tensor_type == 'r':  # refinement method
    print('applying refinement method')
    tensor = tf.CalcAnisoTensorProjOptimized(ref_dirs, measurements, n=10)
