"""Personalized recommendations, served with NumPy only.

The models are trained offline in ml/ and exported to recsys/artifacts/.
Nothing here needs LightGBM, SciPy or PyTorch, so it fits in Vercel's
function size limit next to the rest of the API.
"""
