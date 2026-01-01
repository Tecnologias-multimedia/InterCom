def encode_tree_predict(coeffs, band_ids, roots, children, cdfs, alpha=0.5):
    enc = IntArithmeticEncoder()

    def visit(i, parent_zero, parent_mag=0):
        is_zero = int(coeffs[i] == 0)
        pz = 0.98 if parent_zero else 0.85
        enc.encode_bit(is_zero, pz)
        if is_zero:
            return

        # Prediction
        pred = int(round(alpha * parent_mag)) if parent_mag > 0 else 0
        residual = abs(coeffs[i]) - pred
        residual = max(residual, 0)

        # Encode residual
        enc.encode_integer(residual, cdfs[band_ids[i]])

        # Encode sign
        sign = int(coeffs[i] < 0)
        enc.encode_bit(sign, 0.5)

        # Recurse on children
        for j in children.get(i, []):
            visit(j, parent_zero=False, parent_mag=abs(coeffs[i]))

    for r in roots:
        visit(r, parent_zero=False, parent_mag=0)
    return enc.finish()
