import { useQuery } from "@tanstack/react-query";

import { ApiError, getCurrentSession } from "../common/api";
import { sessionQueryKey } from "../common/query";

export function useSession() {
  return useQuery({
    queryKey: sessionQueryKey,
    queryFn: async () => {
      try {
        return await getCurrentSession();
      } catch (error) {
        if (error instanceof ApiError && error.statusCode === 401) {
          return null;
        }
        throw error;
      }
    },
    retry: false,
  });
}
