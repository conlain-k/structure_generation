import h5py
import sys


def main():
    # program name, file 1, file 2
    assert len(sys.argv) == 3
    f1 = h5py.File(sys.argv[1])
    f2 = h5py.File(sys.argv[2])

    k1 = set(f1.keys())
    k2 = set(f1.keys())

    if not k1 == k2:
        print("Keys mismatch!")
        print(f"File 1 has keys {k1}")
        print(f"File 2 has keys {k2}")

    for k in k1:
        if k in k2:
            d1k = f1[k]
            d2k = f2[k]

            if d1k.shape != d2k.shape:
                print(f"Dataset size {k} mismatch!")
                print(f"File 1 has size {d1k.shape}, file 2 has size {d2k.shape}")

            d1k_0 = d1k[0]
            d2k_0 = d2k[0]

            print(d1k_0.shape)
            print(d2k_0.shape)

            diff = abs(d1k_0 - d2k_0).sum()
            if diff >= 1e-8:
                print(f"First entry mismatch for dataset {k}!")
                print(diff)
                print(d1k_0[0, :, 0, 0])
                print(d2k_0[0, :, 0, 0])
                print(d1k_0[0].mean())
                print(d2k_0[0].mean())

        else:
            print("Dataset mismatch!")
            print(f"File 1 has dataset {k} but file 2 doesn't!")


if __name__ == "__main__":
    main()
