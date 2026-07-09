import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit';
import { authApi } from '../../services/api';
import type { UserInfo } from '../../types';

interface AuthState {
  user: UserInfo | null;
  token: string | null;
  loading: boolean;
}

const initialState: AuthState = {
  user: null,
  token: localStorage.getItem('access_token'),
  loading: false,
};

export const login = createAsyncThunk(
  'auth/login',
  async ({ username, password }: { username: string; password: string }) => {
    const response = await authApi.login(username, password);
    const { access_token } = response.data;
    localStorage.setItem('access_token', access_token);
    return access_token;
  }
);

export const fetchMe = createAsyncThunk('auth/fetchMe', async () => {
  const response = await authApi.me();
  return response.data;
});

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout: (state) => {
      state.user = null;
      state.token = null;
      localStorage.removeItem('access_token');
    },
    setToken: (state, action: PayloadAction<string>) => {
      state.token = action.payload;
      localStorage.setItem('access_token', action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.fulfilled, (state, action) => {
        state.token = action.payload;
      })
      .addCase(fetchMe.fulfilled, (state, action) => {
        state.user = action.payload;
      });
  },
});

export const { logout, setToken } = authSlice.actions;
export default authSlice.reducer;
